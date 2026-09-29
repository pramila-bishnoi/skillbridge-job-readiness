import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { studentApi } from "@/api/student";
import { studentDashboardApi } from "@/api/studentDashboard";
import { ApiError, toApiError } from "@/api/client";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorMessage } from "@/components/common/ErrorMessage";
import { LinkButton } from "@/components/common/Button";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { StatCard } from "@/components/dashboard/StatCard";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import type { StudentDashboardSummary } from "@/types/api";

const WORKFLOW_LINKS = [
  { to: "/profile", label: "My Profile", hint: "Resume & extracted skills" },
  { to: "/analyze", label: "Analyze a Job", hint: "Paste a job description" },
  { to: "/compare", label: "Compare Jobs", hint: "Readiness side by side" },
  { to: "/skill-progress", label: "Skill Progress", hint: "Track what you're learning" },
];

export default function StudentDashboardPage() {
  useDocumentTitle("Dashboard");
  const [hasProfile] = useState(Boolean(studentApi.token()));

  const [summary, setSummary] = useState<StudentDashboardSummary | null>(null);
  const [loading, setLoading] = useState(hasProfile);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    if (!hasProfile) return;
    studentDashboardApi
      .get()
      .then(setSummary)
      .catch((caught) => setError(toApiError(caught)))
      .finally(() => setLoading(false));
  }, [hasProfile]);

  if (!hasProfile) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
        <EmptyState
          icon="👋"
          title="Welcome to SkillBridge"
          description="Create your profile to start tracking your readiness for the roles you care about."
          action={<LinkButton to="/profile">Create your profile</LinkButton>}
        />
      </div>
    );
  }

  if (loading) return <LoadingSpinner label="Loading your dashboard…" />;
  if (error) return <ErrorMessage error={error} title="Could not load your dashboard" />;
  if (!summary) return null;

  return (
    <div className="mx-auto max-w-5xl space-y-8 px-4 py-10 sm:px-6">
      <header>
        <p className="text-sm font-semibold uppercase tracking-wide text-brand-700">
          SkillBridge
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
          Your dashboard
        </h1>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Skills tracked" value={summary.tracked_skills_count} />
        <StatCard label="Jobs analyzed" value={summary.analyzed_jobs_count} />
        <StatCard
          label="Average readiness"
          value={
            summary.average_readiness_score === null ? "—" : `${summary.average_readiness_score}%`
          }
        />
        <StatCard label="Confident skills" value={summary.confident_count} />
      </section>

      <section className="card p-6 sm:p-8">
        <h2 className="text-lg font-semibold text-slate-900">Continue your workflow</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {WORKFLOW_LINKS.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className="rounded-lg border border-slate-200 p-4 transition hover:border-brand-300 hover:bg-brand-50/50"
            >
              <span className="block text-sm font-semibold text-slate-900">{link.label}</span>
              <span className="mt-1 block text-xs text-slate-500">{link.hint}</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="card p-6 sm:p-8">
        <h2 className="text-lg font-semibold text-slate-900">Skill progress</h2>
        <div className="mt-3 flex flex-wrap gap-4 text-sm">
          <span className="text-slate-600">Not started: {summary.not_started_count}</span>
          <span className="text-amber-700">Learning: {summary.learning_count}</span>
          <span className="text-brand-700">Practiced: {summary.practiced_count}</span>
          <span className="text-emerald-700">Confident: {summary.confident_count}</span>
        </div>
        <Link
          to="/skill-progress"
          className="mt-4 inline-block text-sm font-medium text-brand-600 hover:underline"
        >
          Manage skill progress →
        </Link>

        {summary.recent_skill_progress.length > 0 && (
          <ul className="mt-4 space-y-1.5 border-t border-slate-100 pt-4">
            {summary.recent_skill_progress.map((entry) => (
              <li key={entry.skill_id} className="flex justify-between text-sm">
                <span className="text-slate-800">{entry.name}</span>
                <span className="text-slate-500">{entry.status.replace("_", " ").toLowerCase()}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card p-6 sm:p-8">
        <h2 className="text-lg font-semibold text-slate-900">Readiness</h2>
        {summary.best_readiness_job ? (
          <p className="mt-2 text-sm text-slate-600">
            Your best match so far:{" "}
            <Link
              to={`/readiness/${summary.best_readiness_job.job_profile_id}`}
              className="font-medium text-brand-700 hover:underline"
            >
              {summary.best_readiness_job.title}
            </Link>{" "}
            at {summary.best_readiness_job.readiness_score}%.
          </p>
        ) : (
          <p className="mt-2 text-sm text-slate-500">
            Analyze a job and run a readiness check to see your best match here.
          </p>
        )}
        <div className="mt-4 flex flex-wrap gap-4">
          <Link to="/analyze" className="text-sm font-medium text-brand-600 hover:underline">
            Analyze a job →
          </Link>
          <Link to="/compare" className="text-sm font-medium text-brand-600 hover:underline">
            Compare saved jobs →
          </Link>
        </div>
      </section>
    </div>
  );
}
