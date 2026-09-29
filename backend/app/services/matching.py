"""Resume–job matching with TF-IDF and cosine similarity.

Why this lives in a service, not a route: scoring is a business rule (how a
candidate is compared to a role) and must be identical at apply-time, on job
edit, and when a recruiter asks for a ranked shortlist.

Why a small in-process implementation instead of scikit-learn: the Fargate
task is 512 MB. Pulling numpy/scipy/sklearn would crowd out the actual
application. The algorithm is the same one: term frequency × smoothed inverse
document frequency, then cosine similarity of the two vectors.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from app.models.application import Application
from app.models.job import Job

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+\-#.]{1,}", re.IGNORECASE)

# Function words that never distinguish a FastAPI role from an HR role.
STOPWORDS = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "if", "then", "else", "for", "of",
        "in", "on", "at", "to", "from", "by", "with", "as", "is", "are", "was",
        "were", "be", "been", "being", "this", "that", "these", "those", "it",
        "its", "we", "our", "you", "your", "they", "their", "he", "she", "his",
        "her", "i", "me", "my", "not", "no", "so", "than", "too", "very", "can",
        "will", "just", "about", "into", "over", "after", "before", "also",
        "have", "has", "had", "do", "does", "did", "would", "should", "could",
        "may", "might", "must", "shall", "using", "used", "use", "via", "per",
        "etc", "including", "across", "within", "without", "among", "such",
        "more", "most", "other", "any", "all", "each", "both", "own", "same",
        "role", "job", "team", "work", "working", "candidate", "looking",
    }
)

MAX_TERMS = 8


@dataclass(frozen=True)
class MatchResult:
    """``score`` is 0–100 so recruiters read a percentage, not a cosine."""

    score: float
    terms: str


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for raw in TOKEN_RE.findall(text.lower()):
        token = raw.strip(".-+#")
        if len(token) < 2 or token in STOPWORDS or token.isdigit():
            continue
        tokens.append(token)
    return tokens


def job_document(job: Job) -> str:
    return " ".join(
        part
        for part in (
            job.title,
            job.department,
            job.location,
            job.description,
            job.responsibilities,
            job.skills,
            job.experience_required,
        )
        if part
    )


def candidate_document(application: Application) -> str:
    return " ".join(
        part
        for part in (
            application.experience,
            application.cover_note,
            application.resume_text,
        )
        if part
    )


def _term_counts(tokens: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    return counts


def _tfidf_vectors(documents: list[str]) -> list[dict[str, float]]:
    """Smoothed TF-IDF over the supplied documents.

    idf(t) = log((N + 1) / (df(t) + 1)) + 1  — the +1s keep a term that appears
    in every document from vanishing, which matters when the corpus is just
    one job plus one resume.
    """
    tokenised = [tokenize(doc) for doc in documents]
    counts = [_term_counts(tokens) for tokens in tokenised]
    n_docs = len(documents)
    df: dict[str, int] = {}
    for bag in counts:
        for term in bag:
            df[term] = df.get(term, 0) + 1

    vectors: list[dict[str, float]] = []
    for tokens, bag in zip(tokenised, counts, strict=True):
        length = max(len(tokens), 1)
        vector: dict[str, float] = {}
        for term, raw in bag.items():
            tf = raw / length
            idf = math.log((n_docs + 1) / (df[term] + 1)) + 1.0
            vector[term] = tf * idf
        vectors.append(vector)
    return vectors


def _dot(left: dict[str, float], right: dict[str, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(weight * right.get(term, 0.0) for term, weight in left.items())


def _norm(vector: dict[str, float]) -> float:
    return math.sqrt(sum(weight * weight for weight in vector.values()))


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    denominator = _norm(left) * _norm(right)
    if denominator == 0:
        return 0.0
    return _dot(left, right) / denominator


def _overlapping_terms(job_vec: dict[str, float], cand_vec: dict[str, float]) -> str:
    scored = [
        (term, job_vec[term] * cand_vec[term])
        for term in job_vec
        if term in cand_vec
    ]
    scored.sort(key=lambda item: item[1], reverse=True)
    return ", ".join(term for term, _ in scored[:MAX_TERMS])


def score_pair(job_text: str, candidate_text: str) -> MatchResult:
    """Pairwise TF-IDF: the job and this candidate are the whole corpus."""
    job_vec, cand_vec = _tfidf_vectors([job_text, candidate_text])
    cosine = cosine_similarity(job_vec, cand_vec)
    return MatchResult(
        score=round(cosine * 100.0, 1),
        terms=_overlapping_terms(job_vec, cand_vec),
    )


def score_application(job: Job, application: Application) -> MatchResult:
    return score_pair(job_document(job), candidate_document(application))


def rank_against_job(job: Job, applications: list[Application]) -> list[tuple[Application, MatchResult]]:
    """TF-IDF fitted on the job plus every candidate, then cosine vs the job.

    Fitting on the whole shortlist makes rare, role-specific terms (FastAPI,
    Terraform) weigh more than words every resume shares. Pairwise scoring at
    apply-time stays stable; this ranking is relative to the current pool.
    """
    if not applications:
        return []

    job_text = job_document(job)
    documents = [job_text, *[candidate_document(app) for app in applications]]
    vectors = _tfidf_vectors(documents)
    job_vec = vectors[0]

    ranked: list[tuple[Application, MatchResult]] = []
    for application, vector in zip(applications, vectors[1:], strict=True):
        cosine = cosine_similarity(job_vec, vector)
        ranked.append(
            (
                application,
                MatchResult(
                    score=round(cosine * 100.0, 1),
                    terms=_overlapping_terms(job_vec, vector),
                ),
            )
        )
    ranked.sort(key=lambda item: (-item[1].score, item[0].id))
    return ranked
