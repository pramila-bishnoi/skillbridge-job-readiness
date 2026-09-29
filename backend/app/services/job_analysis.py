"""Deterministic job-description analysis.

Two independent, regex-based extractions — no external LLM/NLP, in keeping
with the rest of this codebase's matching code (``services/matching.py``,
``services/skill_normalization.py``):

1. ``segment_description`` splits a job description into a "required" span
   and a "preferred" span by looking for common section headings
   ("Requirements:", "Preferred Qualifications", "Nice to have", ...) on
   their own line. If no such heading is found, the whole description is
   treated as required and the preferred span is empty — the spec is explicit
   that preferred skills should only be reported "when they can be determined
   reliably", so an untagged description never produces a guessed preferred
   list.

2. ``extract_experience`` looks for a handful of common experience-requirement
   phrasings ("3-5 years", "5+ years", "minimum 2 years", "3 years of
   experience") and returns both a canonical form and the exact text matched,
   or ``None`` if nothing recognisable is present — it never guesses either.

Callers combine these with ``services/skill_normalization.normalize_skills``
(Phase 2) to turn the required/preferred spans into canonical skill matches;
this module has no knowledge of the skill catalog itself.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

REQUIRED_HEADERS = frozenset(
    {
        "requirements",
        "required skills",
        "required qualifications",
        "minimum qualifications",
        "minimum requirements",
        "must have",
        "must-have",
        "what you'll need",
        "what you need",
        "qualifications",
        "you have",
    }
)
PREFERRED_HEADERS = frozenset(
    {
        "preferred",
        "preferred skills",
        "preferred qualifications",
        "nice to have",
        "nice-to-have",
        "bonus",
        "bonus points",
        "good to have",
        "a plus",
        "pluses",
        "it's a plus if",
    }
)

_HEADER_STRIP = ":#-*• \t"


def _normalize_header(line: str) -> str:
    return line.strip().strip(_HEADER_STRIP).casefold()


@dataclass(frozen=True)
class SegmentedDescription:
    required_text: str
    preferred_text: str
    sections_detected: bool


def segment_description(description: str) -> SegmentedDescription:
    """Split ``description`` into required/preferred spans by section heading.

    A line is treated as a heading only when, after stripping bullet/heading
    punctuation, it matches one of the known phrases *exactly* — a JD
    mentioning "the following requirements must be met" mid-paragraph is not
    mistaken for a "Requirements:" heading, since that whole sentence does not
    equal a known phrase.
    """
    required_lines: list[str] = []
    preferred_lines: list[str] = []
    general_lines: list[str] = []
    section: str | None = None
    sections_detected = False

    for raw_line in description.splitlines():
        header = _normalize_header(raw_line)
        if header in REQUIRED_HEADERS:
            section = "required"
            sections_detected = True
            continue
        if header in PREFERRED_HEADERS:
            section = "preferred"
            sections_detected = True
            continue
        if section == "required":
            required_lines.append(raw_line)
        elif section == "preferred":
            preferred_lines.append(raw_line)
        else:
            general_lines.append(raw_line)

    if not sections_detected:
        return SegmentedDescription(
            required_text=description, preferred_text="", sections_detected=False
        )

    # Text before the first heading (an intro/summary paragraph) is folded
    # into "required" rather than dropped or guessed as "preferred".
    required_text = "\n".join([*required_lines, *general_lines])
    preferred_text = "\n".join(preferred_lines)
    return SegmentedDescription(
        required_text=required_text, preferred_text=preferred_text, sections_detected=True
    )


@dataclass(frozen=True)
class ExperienceMatch:
    required: str
    evidence: str


# Checked in this order: a range or explicit "+" is more informative than a
# bare number, and must be checked first so "3-5 years" is not reported as
# just "5 years" by the bare-number pattern matching part of it.
_RANGE_RE = re.compile(r"(\d{1,2})\s*(?:-|–|to)\s*(\d{1,2})\+?\s*years?", re.IGNORECASE)
_PLUS_RE = re.compile(r"(\d{1,2})\+\s*years?", re.IGNORECASE)
_MINIMUM_RE = re.compile(
    r"(?:minimum|at least|min\.?)\s*(?:of\s*)?(\d{1,2})\s*years?", re.IGNORECASE
)
_BARE_RE = re.compile(r"(\d{1,2})\s*years?(?:\s*of\s*experience)?", re.IGNORECASE)


def extract_experience(description: str) -> ExperienceMatch | None:
    if match := _RANGE_RE.search(description):
        low, high = match.group(1), match.group(2)
        return ExperienceMatch(required=f"{low}-{high} years", evidence=match.group(0))
    if match := _PLUS_RE.search(description):
        return ExperienceMatch(required=f"{match.group(1)}+ years", evidence=match.group(0))
    if match := _MINIMUM_RE.search(description):
        return ExperienceMatch(required=f"{match.group(1)}+ years", evidence=match.group(0))
    if match := _BARE_RE.search(description):
        return ExperienceMatch(required=f"{match.group(1)} years", evidence=match.group(0))
    return None
