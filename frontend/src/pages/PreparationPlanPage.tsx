import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { preparationApi } from "@/api/preparation";
import { ApiError, toApiError } from "@/api/client";
import { Button, LinkButton } from "@/components/common/Button";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorMessage } from "@/components/common/ErrorMessage";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { classNames } from "@/utils/format";
import type {
  PreparationItem,
  PreparationItemStatus,
  PreparationPlanDetail,
  SkillGapImportance,
} from "@/types/api";

const PRIORITY_STYLE: Record<SkillGapImportance, string> = {
  HIGH: "bg-red-100 text-red-700",
  MEDIUM: "bg-amber-100 text-amber-700",
  LOW: "bg-slate-100 text-slate-600",
};

const STATUS_OPTIONS: { value: PreparationItemStatus; label: string }[] = [
  { value: "NOT_STARTED", label: "Not started" },
  { value: "IN_PROGRESS", label: "In progress" },
  { value: "COMPLETED", label: "Completed" },
];

function ProgressBar({ plan }: { plan: PreparationPlanDetail }) {
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <p className="text-sm font-semibold text-slate-500">Overall progress</p>
        <p className="text-2xl font-bold tabular-nums text-slate-900">
          {plan.progress_percent}%
        </p>
      </div>
      <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-emerald-500 transition-all"
          style={{ width: `${plan.progress_percent}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-slate-500">
        {plan.completed_items} completed · {plan.in_progress_items} in progress ·{" "}
        {plan.not_started_items} not started · {plan.total_items} total
      </p>
    </div>
  );
}

function ItemCard({
  item,
  onStatusChange,
  updating,
}: {
  item: PreparationItem;
  onStatusChange: (itemId: number, status: PreparationItemStatus) => void;
  updating: boolean;
}) {
  return (
    <li className="card space-y-2 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className={classNames(
              "rounded px-2 py-0.5 text-xs font-semibold",
              PRIORITY_STYLE[item.priority],
            )}
          >
            {item.priority}
          </span>
          <span className="font-medium text-slate-900">{item.name}</span>
          {item.gap_type === "RELATED" && (
            <span className="text-xs text-amber-600">related skill only</span>
          )}
        </div>
        <select
          aria-label={`Status for ${item.name}`}
          className="field-control w-auto text-xs"
          value={item.status}
          disabled={updating}
          onChange={(event) =>
            onStatusChange(item.id, event.target.value as PreparationItemStatus)
          }
        >
          {STATUS_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      <p className="text-sm text-slate-600">{item.reason}</p>
      <p className="text-xs text-slate-500">
        <span className="font-semibold text-slate-600">Learning focus: </span>
        {item.learning_focus}
      </p>
    </li>
  );
}

export default function PreparationPlanPage() {
  const { jobProfileId } = useParams<{ jobProfileId: string }>();
  const id = Number(jobProfileId);
  useDocumentTitle("Preparation plan");

  const [plan, setPlan] = useState<PreparationPlanDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [updatingItemId, setUpdatingItemId] = useState<number | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [notFound, setNotFound] = useState<"plan" | "analysis" | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    preparationApi
      .get(id)
      .then((result) => {
        setPlan(result);
        setNotFound(null);
      })
      .catch((caught) => {
        const apiError = toApiError(caught);
        if (apiError.code === "PREPARATION_PLAN_NOT_FOUND") setNotFound("plan");
        else if (apiError.code === "MATCH_ANALYSIS_NOT_FOUND") setNotFound("analysis");
        else setError(apiError);
      })
      .finally(() => setLoading(false));
  };

  useEffect(load, [id]);

  const generatePlan = async () => {
    setError(null);
    setGenerating(true);
    try {
      const result = await preparationApi.generate(id);
      setPlan(result);
      setNotFound(null);
    } catch (caught) {
      const apiError = toApiError(caught);
      if (apiError.code === "MATCH_ANALYSIS_NOT_FOUND") setNotFound("analysis");
      else setError(apiError);
    } finally {
      setGenerating(false);
    }
  };

  const changeStatus = async (itemId: number, status: PreparationItemStatus) => {
    setError(null);
    setUpdatingItemId(itemId);
    try {
      setPlan(await preparationApi.updateItemStatus(id, itemId, status));
    } catch (caught) {
      setError(toApiError(caught));
    } finally {
      setUpdatingItemId(null);
    }
  };

  if (loading) return <LoadingSpinner label="Loading preparation plan…" />;

  const grouped: Record<SkillGapImportance, PreparationItem[]> = { HIGH: [], MEDIUM: [], LOW: [] };
  for (const item of plan?.items ?? []) {
    grouped[item.priority].push(item);
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8 px-4 py-10 sm:px-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-brand-700">
            Preparation Plan
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
            {plan?.job_title ?? "This job"}
          </h1>
          <Link
            to={`/readiness/${id}`}
            className="mt-1 inline-block text-sm text-brand-600 hover:underline"
          >
            ← Back to readiness
          </Link>
        </div>
        {plan && (
          <Button onClick={generatePlan} loading={generating} variant="secondary">
            Regenerate plan
          </Button>
        )}
      </header>

      {error && <ErrorMessage error={error} title="Could not load preparation plan" onRetry={load} />}

      {!plan && notFound === "analysis" && !error && (
        <EmptyState
          icon="📈"
          title="Run a readiness check first"
          description="A preparation plan is built from a job's skill gaps, so a readiness analysis has to exist first."
          action={<LinkButton to={`/readiness/${id}`}>Run readiness analysis →</LinkButton>}
        />
      )}

      {!plan && notFound === "plan" && !error && (
        <EmptyState
          icon="📝"
          title="No preparation plan yet"
          description="Generate a plan to turn your missing skills into a prioritized, explainable study list."
          action={
            <Button onClick={generatePlan} loading={generating}>
              Generate plan
            </Button>
          }
        />
      )}

      {plan && (
        <>
          <section className="card p-6 sm:p-8">
            <ProgressBar plan={plan} />
          </section>

          {plan.items.length === 0 ? (
            <EmptyState
              icon="✅"
              title="Nothing to prepare for"
              description="Every required and preferred skill was matched or related the last time readiness was analyzed."
            />
          ) : (
            (["HIGH", "MEDIUM", "LOW"] as SkillGapImportance[]).map((priority) =>
              grouped[priority].length ? (
                <section key={priority} className="space-y-3">
                  <h2 className="text-lg font-semibold text-slate-900">
                    {priority === "HIGH"
                      ? "High priority"
                      : priority === "MEDIUM"
                        ? "Medium priority"
                        : "Low priority"}
                  </h2>
                  <ul className="space-y-3">
                    {grouped[priority].map((item) => (
                      <ItemCard
                        key={item.id}
                        item={item}
                        onStatusChange={changeStatus}
                        updating={updatingItemId === item.id}
                      />
                    ))}
                  </ul>
                </section>
              ) : null,
            )
          )}
        </>
      )}
    </div>
  );
}
