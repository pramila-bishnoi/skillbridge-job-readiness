import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { readinessApi } from "@/api/readiness";
import { ApiError, toApiError } from "@/api/client";
import { Button } from "@/components/common/Button";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorMessage } from "@/components/common/ErrorMessage";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { classNames } from "@/utils/format";
import type { MatchAnalysisDetail, SkillGap, SkillGapImportance } from "@/types/api";

const IMPORTANCE_ORDER: Record<SkillGapImportance, number> = {
  HIGH: 0,
  MEDIUM: 1,
  LOW: 2,
};

const IMPORTANCE_STYLE: Record<SkillGapImportance, string> = {
  HIGH: "bg-red-100 text-red-700",
  MEDIUM: "bg-amber-100 text-amber-700",
  LOW: "bg-slate-100 text-slate-600",
};

function ReadinessGauge({ score }: { score: number }) {
  const tone =
    score >= 75 ? "text-emerald-600" : score >= 50 ? "text-amber-600" : "text-red-600";
  return (
    <div>
      <p className="text-sm font-semibold text-slate-500">Overall readiness</p>
      <p className={classNames("text-5xl font-bold tabular-nums", tone)}>{score}%</p>
    </div>
  );
}

/** A visible progress bar per scoring component — the same numbers the
 * dl below states in text, just easier to scan at a glance. Never a
 * substitute for the text (colour alone never carries the meaning here). */
function ComponentBar({ value }: { value: number }) {
  const tone = value >= 75 ? "bg-emerald-500" : value >= 50 ? "bg-amber-500" : "bg-red-400";
  return (
    <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
      <div
        className={classNames("h-full rounded-full", tone)}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}

/** Evidence is shown as visible text under every skill, not only in a
 * hover `title` — a title-only tooltip is invisible on touch devices, and
 * the whole point of an explainable score is that the evidence is not
 * hidden behind an interaction. */
function EvidenceLine({ evidence }: { evidence: string }) {
  if (!evidence) return null;
  return <p className="mt-0.5 text-xs text-slate-500">{evidence}</p>;
}

function SkillRow({ skill }: { skill: SkillGap }) {
  const isMatched = skill.gap_type === "MATCHED";
  const isRelated = skill.gap_type === "RELATED";
  return (
    <li className="flex items-start gap-2 text-sm">
      <span
        aria-hidden="true"
        className={classNames(
          "mt-0.5 font-bold",
          isMatched && "text-emerald-600",
          isRelated && "text-amber-600",
          !isMatched && !isRelated && "text-red-500",
        )}
      >
        {isMatched ? "✓" : isRelated ? "~" : "✗"}
      </span>
      <div>
        <span className="text-slate-800">{skill.name}</span>
        {isRelated && skill.related_to_skill_name && (
          <span className="ml-1.5 text-xs text-slate-500">
            (related to your {skill.related_to_skill_name})
          </span>
        )}
        <EvidenceLine evidence={skill.evidence} />
      </div>
    </li>
  );
}

function SkillSection({ title, skills }: { title: string; skills: SkillGap[] }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      {skills.length ? (
        <ul className="mt-2 space-y-2.5">
          {skills.map((skill) => (
            <SkillRow key={skill.skill_id} skill={skill} />
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-slate-500">None listed for this job.</p>
      )}
    </div>
  );
}

function GapRow({ gap }: { gap: SkillGap }) {
  return (
    <li className="flex items-start gap-3 text-sm">
      <span
        className={classNames(
          "mt-0.5 w-16 shrink-0 rounded px-2 py-0.5 text-center text-xs font-semibold",
          IMPORTANCE_STYLE[gap.importance],
        )}
      >
        {gap.importance}
      </span>
      <div>
        <span className="text-slate-800">{gap.name}</span>
        {gap.gap_type === "RELATED" && gap.related_to_skill_name && (
          <span className="ml-1.5 text-xs text-slate-500">
            (you know {gap.related_to_skill_name})
          </span>
        )}
        <EvidenceLine evidence={gap.evidence} />
      </div>
    </li>
  );
}

/** The score explanation — deliberately the first thing shown after the
 * headline number, not buried below the skill lists, since "explainable
 * first" is the whole point of this page. Weights/formula are fixed
 * (Phase 4) and never computed here — this only renders what the API
 * already returned. */
function WhyPanel({ analysis }: { analysis: MatchAnalysisDetail }) {
  return (
    <section className="card space-y-4 p-6 sm:p-8">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">
          Why {analysis.readiness_score}%?
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          Four deterministic, fixed-weight components are combined — no part of
          this number is a guess, and every component below is something you
          can check yourself.
        </p>
      </div>
      <dl className="space-y-4 text-sm text-slate-700">
        <div>
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <dt className="font-medium">Required skill coverage · weighted 45%</dt>
            <dd className="tabular-nums">
              {analysis.required_matched_count}/{analysis.required_total_count} (
              {analysis.required_skill_coverage}%)
            </dd>
          </div>
          <ComponentBar value={analysis.required_skill_coverage} />
        </div>
        <div>
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <dt className="font-medium">Preferred skill coverage · weighted 15%</dt>
            <dd className="tabular-nums">
              {analysis.preferred_matched_count}/{analysis.preferred_total_count} (
              {analysis.preferred_skill_coverage}%)
            </dd>
          </div>
          <ComponentBar value={analysis.preferred_skill_coverage} />
        </div>
        <div>
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <dt className="font-medium">Experience / project evidence · weighted 20%</dt>
            <dd className="tabular-nums">{analysis.experience_score}%</dd>
          </div>
          <ComponentBar value={analysis.experience_score} />
          {analysis.experience_evidence && (
            <p className="mt-1 text-xs text-slate-500">{analysis.experience_evidence}</p>
          )}
        </div>
        <div>
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <dt className="font-medium">Text similarity · weighted 20%</dt>
            <dd className="tabular-nums">{analysis.text_similarity_score}%</dd>
          </div>
          <ComponentBar value={analysis.text_similarity_score} />
          {analysis.text_similarity_terms && (
            <p className="mt-1 text-xs text-slate-500">
              Overlapping terms: {analysis.text_similarity_terms}
            </p>
          )}
        </div>
      </dl>
      <p className="border-t border-slate-100 pt-3 text-xs text-slate-400">
        Score version {analysis.score_version} · a preparation aid based on your
        current profile and this rule set, not a hiring decision.
      </p>
    </section>
  );
}

export default function JobReadinessPage() {
  const { jobProfileId } = useParams<{ jobProfileId: string }>();
  const id = Number(jobProfileId);
  useDocumentTitle("Job readiness");

  const [analysis, setAnalysis] = useState<MatchAnalysisDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [notFound, setNotFound] = useState(false);

  const load = () => {
    setLoading(true);
    setError(null);
    readinessApi
      .get(id)
      .then((result) => {
        setAnalysis(result);
        setNotFound(false);
      })
      .catch((caught) => {
        const apiError = toApiError(caught);
        if (apiError.code === "MATCH_ANALYSIS_NOT_FOUND") {
          setNotFound(true);
        } else {
          setError(apiError);
        }
      })
      .finally(() => setLoading(false));
  };

  useEffect(load, [id]);

  const runAnalysis = async () => {
    setError(null);
    setAnalyzing(true);
    try {
      const result = await readinessApi.analyze(id);
      setAnalysis(result);
      setNotFound(false);
    } catch (caught) {
      setError(toApiError(caught));
    } finally {
      setAnalyzing(false);
    }
  };

  if (loading) return <LoadingSpinner label="Loading readiness…" />;

  const requiredSkills = analysis
    ? [
        ...analysis.matched_skills,
        ...analysis.missing_skills,
        ...analysis.skill_gaps.filter((g) => g.gap_type === "RELATED"),
      ].filter((s) => s.requirement_type === "REQUIRED")
    : [];
  const preferredSkills = analysis
    ? [
        ...analysis.matched_skills,
        ...analysis.missing_skills,
        ...analysis.skill_gaps.filter((g) => g.gap_type === "RELATED"),
      ].filter((s) => s.requirement_type === "PREFERRED")
    : [];
  const sortedGaps = analysis
    ? [...analysis.skill_gaps].sort(
        (a, b) => IMPORTANCE_ORDER[a.importance] - IMPORTANCE_ORDER[b.importance],
      )
    : [];

  return (
    <div className="mx-auto max-w-4xl space-y-8 px-4 py-10 sm:px-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-brand-700">
            Job Readiness
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
            {analysis?.job_title ?? "This job"}
          </h1>
          <Link to="/analyze" className="mt-1 inline-block text-sm text-brand-600 hover:underline">
            ← Back to analyzed jobs
          </Link>
        </div>
        {analysis && (
          <Button onClick={runAnalysis} loading={analyzing} variant="secondary">
            Re-run analysis
          </Button>
        )}
      </header>

      {error && <ErrorMessage error={error} title="Could not load readiness" onRetry={load} />}

      {!analysis && notFound && !error && (
        <EmptyState
          icon="📈"
          title="No readiness analysis yet"
          description="Run a readiness check to compare your normalized skills against this job's required and preferred skills."
          action={
            <Button onClick={runAnalysis} loading={analyzing}>
              Run analysis
            </Button>
          }
        />
      )}

      {analysis && (
        <>
          <section className="card space-y-4 p-6 sm:p-8">
            <ReadinessGauge score={analysis.readiness_score} />
            <Link
              to={`/interview-prep/${id}`}
              className="inline-block text-sm font-medium text-brand-600 hover:underline"
            >
              Practice interview questions for this job →
            </Link>
          </section>

          <WhyPanel analysis={analysis} />

          <section className="card grid gap-8 p-6 sm:grid-cols-2 sm:p-8">
            <SkillSection title="Required skills" skills={requiredSkills} />
            <SkillSection title="Preferred skills" skills={preferredSkills} />
          </section>

          <section className="card p-6 sm:p-8">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-semibold text-slate-900">Skill gaps</h2>
              {sortedGaps.length > 0 && (
                <Link
                  to={`/preparation/${id}`}
                  className="text-sm font-medium text-brand-600 hover:underline"
                >
                  Build a preparation plan →
                </Link>
              )}
            </div>
            {sortedGaps.length ? (
              <ul className="mt-3 space-y-3">
                {sortedGaps.map((gap) => (
                  <GapRow key={gap.skill_id} gap={gap} />
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-sm text-slate-500">
                No gaps — every required and preferred skill was matched.
              </p>
            )}
          </section>
        </>
      )}
    </div>
  );
}
