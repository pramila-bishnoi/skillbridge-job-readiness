import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { jobAnalysisApi } from "@/api/jobAnalysis";
import { jobComparisonApi } from "@/api/jobComparison";
import { studentApi } from "@/api/student";
import { ApiError, toApiError } from "@/api/client";
import { Button, LinkButton } from "@/components/common/Button";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorMessage } from "@/components/common/ErrorMessage";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { classNames } from "@/utils/format";
import type { JobComparisonResult, JobProfileSummary } from "@/types/api";

const MIN_JOBS = 2;
const MAX_JOBS = 5;

function ReadinessCell({ score }: { score: number }) {
  const tone =
    score >= 75 ? "text-emerald-600" : score >= 50 ? "text-amber-600" : "text-red-600";
  return <span className={classNames("text-xl font-bold tabular-nums", tone)}>{score}%</span>;
}

function SkillChipList({ skills, tone }: { skills: string[]; tone: string }) {
  if (!skills.length) {
    return <span className="text-xs text-slate-400">None</span>;
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {skills.map((skill) => (
        <span key={skill} className={classNames("rounded-full px-2 py-0.5 text-xs font-medium", tone)}>
          {skill}
        </span>
      ))}
    </div>
  );
}

export default function JobComparisonPage() {
  useDocumentTitle("Compare jobs");
  const [hasProfile] = useState(Boolean(studentApi.token()));

  const [savedJobs, setSavedJobs] = useState<JobProfileSummary[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [result, setResult] = useState<JobComparisonResult | null>(null);
  const [loadingJobs, setLoadingJobs] = useState(hasProfile);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [jobsNotAnalyzed, setJobsNotAnalyzed] = useState(false);

  useEffect(() => {
    if (!hasProfile) return;
    jobAnalysisApi
      .list()
      .then(setSavedJobs)
      .catch((caught) => setError(toApiError(caught)))
      .finally(() => setLoadingJobs(false));
  }, [hasProfile]);

  const toggleJob = (jobId: number) => {
    setResult(null);
    setJobsNotAnalyzed(false);
    setSelectedIds((current) => {
      if (current.includes(jobId)) return current.filter((id) => id !== jobId);
      if (current.length >= MAX_JOBS) return current;
      return [...current, jobId];
    });
  };

  const compare = async () => {
    setError(null);
    setJobsNotAnalyzed(false);
    setComparing(true);
    try {
      setResult(await jobComparisonApi.compare(selectedIds));
    } catch (caught) {
      const apiError = toApiError(caught);
      if (apiError.code === "JOBS_NOT_ANALYZED") setJobsNotAnalyzed(true);
      else setError(apiError);
    } finally {
      setComparing(false);
    }
  };

  if (!hasProfile) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
        <EmptyState
          icon="📊"
          title="Create a profile to compare jobs"
          description="Job comparison is tied to your SkillBridge profile. Create one first, then analyze a couple of jobs to compare them here."
          action={<LinkButton to="/profile">Create your profile</LinkButton>}
        />
      </div>
    );
  }

  if (loadingJobs) return <LoadingSpinner label="Loading your saved jobs…" />;

  return (
    <div className="mx-auto max-w-5xl space-y-8 px-4 py-10 sm:px-6">
      <header>
        <p className="text-sm font-semibold uppercase tracking-wide text-brand-700">
          Job Comparison
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
          Compare your analyzed jobs
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-slate-600">
          Pick {MIN_JOBS}–{MAX_JOBS} saved jobs to see their readiness scores,
          matched/missing skills, and shared gaps side by side.
        </p>
      </header>

      {error && <ErrorMessage error={error} title="Could not compare these jobs" />}

      {jobsNotAnalyzed && (
        <div className="card p-4 text-sm text-amber-700">
          Run a readiness analysis for every selected job first, then compare again.
        </div>
      )}

      {savedJobs.length === 0 ? (
        <EmptyState
          icon="📊"
          title="No saved jobs yet"
          description="Analyze a job description first, then come back here to compare it against others."
          action={
            <Link to="/analyze" className="text-sm font-medium text-brand-600 hover:underline">
              Analyze a job →
            </Link>
          }
        />
      ) : (
        <>
          <section className="card p-6 sm:p-8">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-sm font-semibold text-slate-900">
                Select jobs ({selectedIds.length}/{MAX_JOBS})
              </h2>
              <Button
                onClick={compare}
                loading={comparing}
                disabled={selectedIds.length < MIN_JOBS}
              >
                Compare
              </Button>
            </div>
            <ul className="mt-4 grid gap-2 sm:grid-cols-2">
              {savedJobs.map((job) => (
                <li key={job.id}>
                  <label
                    className={classNames(
                      "flex cursor-pointer items-start gap-2 rounded-lg border p-3 text-sm",
                      selectedIds.includes(job.id)
                        ? "border-brand-400 bg-brand-50"
                        : "border-slate-200",
                    )}
                  >
                    <input
                      type="checkbox"
                      className="mt-0.5 h-4 w-4 rounded border-slate-300"
                      checked={selectedIds.includes(job.id)}
                      onChange={() => toggleJob(job.id)}
                      disabled={!selectedIds.includes(job.id) && selectedIds.length >= MAX_JOBS}
                    />
                    <span>
                      <span className="block font-medium text-slate-900">{job.title}</span>
                      {job.company && <span className="text-xs text-slate-500">{job.company}</span>}
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          </section>

          {result && (
            <>
              <section className="card overflow-x-auto p-6 sm:p-8">
                <h2 className="text-lg font-semibold text-slate-900">Readiness side by side</h2>
                <table className="mt-4 w-full min-w-[480px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-xs uppercase text-slate-500">
                      <th className="py-2 pr-4">Job</th>
                      <th className="py-2 pr-4">Readiness</th>
                      <th className="py-2 pr-4">Required</th>
                      <th className="py-2 pr-4">Preferred</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.jobs.map((job) => (
                      <tr key={job.job_profile_id} className="border-b border-slate-100 align-top">
                        <td className="py-3 pr-4">
                          <Link
                            to={`/readiness/${job.job_profile_id}`}
                            className="font-medium text-brand-700 hover:underline"
                          >
                            {job.title}
                          </Link>
                          {job.company && (
                            <span className="block text-xs text-slate-500">{job.company}</span>
                          )}
                        </td>
                        <td className="py-3 pr-4">
                          <ReadinessCell score={job.readiness_score} />
                        </td>
                        <td className="py-3 pr-4">{job.required_skill_coverage}%</td>
                        <td className="py-3 pr-4">{job.preferred_skill_coverage}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>

              <section className="card grid gap-6 p-6 sm:grid-cols-2 sm:p-8">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">
                    Skills every job cares about
                  </h3>
                  <div className="mt-2">
                    <SkillChipList
                      skills={result.common_skills}
                      tone="bg-slate-100 text-slate-700"
                    />
                  </div>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">
                    Gaps that hurt every job
                  </h3>
                  <div className="mt-2">
                    <SkillChipList
                      skills={result.common_missing_skills}
                      tone="bg-red-100 text-red-700"
                    />
                  </div>
                </div>
              </section>

              <section className="space-y-4">
                <h3 className="text-sm font-semibold text-slate-900">Per-job breakdown</h3>
                {result.jobs.map((job) => (
                  <div key={job.job_profile_id} className="card p-4">
                    <p className="text-sm font-medium text-slate-900">{job.title}</p>
                    <div className="mt-2 grid gap-3 sm:grid-cols-3">
                      <div>
                        <p className="text-xs font-semibold uppercase text-slate-500">Matched</p>
                        <div className="mt-1">
                          <SkillChipList
                            skills={job.matched_skills}
                            tone="bg-emerald-100 text-emerald-700"
                          />
                        </div>
                      </div>
                      <div>
                        <p className="text-xs font-semibold uppercase text-slate-500">Missing</p>
                        <div className="mt-1">
                          <SkillChipList skills={job.missing_skills} tone="bg-red-100 text-red-700" />
                        </div>
                      </div>
                      <div>
                        <p className="text-xs font-semibold uppercase text-slate-500">
                          Unique to this job
                        </p>
                        <div className="mt-1">
                          <SkillChipList
                            skills={job.unique_missing_skills}
                            tone="bg-amber-100 text-amber-700"
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </section>
            </>
          )}
        </>
      )}
    </div>
  );
}
