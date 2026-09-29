import { useEffect, useMemo, useState } from "react";
import { skillProgressApi } from "@/api/skillProgress";
import { studentApi } from "@/api/student";
import { ApiError, toApiError } from "@/api/client";
import { Button, LinkButton } from "@/components/common/Button";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorMessage } from "@/components/common/ErrorMessage";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { SelectField } from "@/components/common/FormField";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import type { SkillCatalogEntry, SkillProgressEntry, SkillProgressStatus } from "@/types/api";

const STATUS_OPTIONS: { value: SkillProgressStatus; label: string }[] = [
  { value: "NOT_STARTED", label: "Not started" },
  { value: "LEARNING", label: "Learning" },
  { value: "PRACTICED", label: "Practiced" },
  { value: "CONFIDENT", label: "Confident" },
];

const STATUS_STYLE: Record<SkillProgressStatus, string> = {
  NOT_STARTED: "bg-slate-100 text-slate-600",
  LEARNING: "bg-amber-100 text-amber-700",
  PRACTICED: "bg-brand-50 text-brand-700",
  CONFIDENT: "bg-emerald-100 text-emerald-700",
};

function TrackedSkillRow({
  entry,
  onChange,
  updating,
}: {
  entry: SkillProgressEntry;
  onChange: (skillId: number, status: SkillProgressStatus) => void;
  updating: boolean;
}) {
  return (
    <li className="card flex flex-wrap items-center justify-between gap-3 p-4">
      <div>
        <span className="font-medium text-slate-900">{entry.name}</span>
        {entry.category && <span className="ml-2 text-xs text-slate-500">{entry.category}</span>}
        <span
          className={`ml-2 rounded-full px-2 py-0.5 text-xs font-semibold ${STATUS_STYLE[entry.status]}`}
        >
          {STATUS_OPTIONS.find((o) => o.value === entry.status)?.label}
        </span>
      </div>
      <select
        aria-label={`Progress for ${entry.name}`}
        className="field-control w-auto text-sm"
        value={entry.status}
        disabled={updating}
        onChange={(event) => onChange(entry.skill_id, event.target.value as SkillProgressStatus)}
      >
        {STATUS_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </li>
  );
}

export default function SkillProgressPage() {
  useDocumentTitle("Skill progress");
  const [hasProfile] = useState(Boolean(studentApi.token()));

  const [tracked, setTracked] = useState<SkillProgressEntry[]>([]);
  const [catalog, setCatalog] = useState<SkillCatalogEntry[]>([]);
  const [loading, setLoading] = useState(hasProfile);
  const [error, setError] = useState<ApiError | null>(null);
  const [updatingSkillId, setUpdatingSkillId] = useState<number | null>(null);

  const [newSkillId, setNewSkillId] = useState("");
  const [newStatus, setNewStatus] = useState<SkillProgressStatus>("LEARNING");
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    if (!hasProfile) return;
    Promise.all([skillProgressApi.list(), skillProgressApi.listCatalog()])
      .then(([progress, skills]) => {
        setTracked(progress);
        setCatalog(skills);
      })
      .catch((caught) => setError(toApiError(caught)))
      .finally(() => setLoading(false));
  }, [hasProfile]);

  const trackedIds = useMemo(() => new Set(tracked.map((entry) => entry.skill_id)), [tracked]);
  const untracked = useMemo(
    () => catalog.filter((skill) => !trackedIds.has(skill.skill_id)),
    [catalog, trackedIds],
  );

  const updateStatus = async (skillId: number, status: SkillProgressStatus) => {
    setError(null);
    setUpdatingSkillId(skillId);
    try {
      const updated = await skillProgressApi.update(skillId, status);
      setTracked((current) => {
        const others = current.filter((entry) => entry.skill_id !== skillId);
        return [updated, ...others];
      });
    } catch (caught) {
      setError(toApiError(caught));
    } finally {
      setUpdatingSkillId(null);
    }
  };

  const addSkill = async () => {
    if (!newSkillId) return;
    setError(null);
    setAdding(true);
    try {
      const updated = await skillProgressApi.update(Number(newSkillId), newStatus);
      setTracked((current) => [updated, ...current]);
      setNewSkillId("");
      setNewStatus("LEARNING");
    } catch (caught) {
      setError(toApiError(caught));
    } finally {
      setAdding(false);
    }
  };

  if (!hasProfile) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
        <EmptyState
          icon="🧭"
          title="Create a profile to track skill progress"
          description="Skill progress is tied to your SkillBridge profile. Create one first, then come back here to mark what you're learning."
          action={<LinkButton to="/profile">Create your profile</LinkButton>}
        />
      </div>
    );
  }

  if (loading) return <LoadingSpinner label="Loading skill progress…" />;

  return (
    <div className="mx-auto max-w-3xl space-y-8 px-4 py-10 sm:px-6">
      <header>
        <p className="text-sm font-semibold uppercase tracking-wide text-brand-700">
          Skill Progress
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
          Track how you're improving
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-slate-600">
          Mark any skill — whether it's already on your resume or one you're
          just starting to learn — as Not started, Learning, Practiced, or
          Confident.
        </p>
      </header>

      {error && <ErrorMessage error={error} title="Could not update skill progress" />}

      <section className="card space-y-4 p-6 sm:p-8">
        <h2 className="text-sm font-semibold text-slate-900">Track a new skill</h2>
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[200px] flex-1">
            <SelectField
              label="Skill"
              value={newSkillId}
              onChange={(event) => setNewSkillId(event.target.value)}
              placeholder="Choose a skill…"
              options={untracked.map((skill) => ({
                value: String(skill.skill_id),
                label: skill.name,
              }))}
            />
          </div>
          <div className="w-40">
            <SelectField
              label="Status"
              value={newStatus}
              onChange={(event) => setNewStatus(event.target.value as SkillProgressStatus)}
              options={STATUS_OPTIONS}
            />
          </div>
          <Button onClick={addSkill} loading={adding} disabled={!newSkillId}>
            Add
          </Button>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-slate-900">
          Your tracked skills ({tracked.length})
        </h2>
        {tracked.length ? (
          <ul className="space-y-2">
            {tracked.map((entry) => (
              <TrackedSkillRow
                key={entry.skill_id}
                entry={entry}
                onChange={updateStatus}
                updating={updatingSkillId === entry.skill_id}
              />
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-500">
            Nothing tracked yet — add a skill above to get started.
          </p>
        )}
      </section>
    </div>
  );
}
