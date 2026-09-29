import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { interviewPrepApi } from "@/api/interviewPrep";
import { ApiError, toApiError } from "@/api/client";
import { Button, LinkButton } from "@/components/common/Button";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorMessage } from "@/components/common/ErrorMessage";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { classNames } from "@/utils/format";
import type {
  InterviewCategory,
  InterviewDifficulty,
  InterviewPrepDetail,
  InterviewQuestion,
} from "@/types/api";

const CATEGORY_LABELS: Record<InterviewCategory, string> = {
  TECHNICAL: "Technical",
  SKILL_GAP: "Skill Gap",
  RESUME_PROJECT: "Resume & Projects",
  ROLE_CONCEPT: "Role & Concept",
};

const CATEGORY_ORDER: InterviewCategory[] = [
  "TECHNICAL",
  "SKILL_GAP",
  "RESUME_PROJECT",
  "ROLE_CONCEPT",
];

const DIFFICULTY_STYLE: Record<InterviewDifficulty, string> = {
  EASY: "bg-slate-100 text-slate-600",
  MEDIUM: "bg-amber-100 text-amber-700",
  HARD: "bg-red-100 text-red-700",
};

function ProgressBar({
  completed,
  total,
  percent,
}: {
  completed: number;
  total: number;
  percent: number;
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <p className="text-sm font-semibold text-slate-500">Overall progress</p>
        <p className="text-2xl font-bold tabular-nums text-slate-900">{percent}%</p>
      </div>
      <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-emerald-500 transition-all"
          style={{ width: `${percent}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-slate-500">
        {completed} of {total} questions reviewed
      </p>
    </div>
  );
}

function QuestionCard({
  question,
  onToggle,
  updating,
}: {
  question: InterviewQuestion;
  onToggle: (questionId: number, completed: boolean) => void;
  updating: boolean;
}) {
  return (
    <li className="card space-y-2 p-4">
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          className="mt-1 h-4 w-4 shrink-0 rounded border-slate-300"
          checked={question.completed}
          disabled={updating}
          onChange={(event) => onToggle(question.id, event.target.checked)}
          aria-label={`Mark reviewed: ${question.question}`}
        />
        <div className="flex-1 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={classNames(
                "rounded px-2 py-0.5 text-xs font-semibold",
                DIFFICULTY_STYLE[question.difficulty],
              )}
            >
              {question.difficulty}
            </span>
            {question.related_skill_name && (
              <span className="rounded bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700">
                {question.related_skill_name}
              </span>
            )}
          </div>
          <p
            className={classNames(
              "text-sm text-slate-800",
              question.completed && "text-slate-400 line-through",
            )}
          >
            {question.question}
          </p>
          <p className="text-xs text-slate-500">{question.reason}</p>
        </div>
      </div>
    </li>
  );
}

export default function InterviewPrepPage() {
  const { jobProfileId } = useParams<{ jobProfileId: string }>();
  const id = Number(jobProfileId);
  useDocumentTitle("Interview prep");

  const [prep, setPrep] = useState<InterviewPrepDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [updatingQuestionId, setUpdatingQuestionId] = useState<number | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [notFound, setNotFound] = useState<"prep" | "analysis" | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    interviewPrepApi
      .get(id)
      .then((result) => {
        setPrep(result);
        setNotFound(null);
      })
      .catch((caught) => {
        const apiError = toApiError(caught);
        if (apiError.code === "INTERVIEW_PREP_NOT_FOUND") setNotFound("prep");
        else if (apiError.code === "MATCH_ANALYSIS_NOT_FOUND") setNotFound("analysis");
        else setError(apiError);
      })
      .finally(() => setLoading(false));
  };

  useEffect(load, [id]);

  const generate = async () => {
    setError(null);
    setGenerating(true);
    try {
      const result = await interviewPrepApi.generate(id);
      setPrep(result);
      setNotFound(null);
    } catch (caught) {
      const apiError = toApiError(caught);
      if (apiError.code === "MATCH_ANALYSIS_NOT_FOUND") setNotFound("analysis");
      else setError(apiError);
    } finally {
      setGenerating(false);
    }
  };

  const toggleQuestion = async (questionId: number, completed: boolean) => {
    setError(null);
    setUpdatingQuestionId(questionId);
    try {
      setPrep(await interviewPrepApi.updateQuestionCompleted(id, questionId, completed));
    } catch (caught) {
      setError(toApiError(caught));
    } finally {
      setUpdatingQuestionId(null);
    }
  };

  if (loading) return <LoadingSpinner label="Loading interview prep…" />;

  const grouped: Record<InterviewCategory, InterviewQuestion[]> = {
    TECHNICAL: [],
    SKILL_GAP: [],
    RESUME_PROJECT: [],
    ROLE_CONCEPT: [],
  };
  for (const question of prep?.questions ?? []) {
    grouped[question.category].push(question);
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8 px-4 py-10 sm:px-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-brand-700">
            Interview Prep
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
            {prep?.job_title ?? "This job"}
          </h1>
          <Link
            to={`/readiness/${id}`}
            className="mt-1 inline-block text-sm text-brand-600 hover:underline"
          >
            ← Back to readiness
          </Link>
        </div>
        {prep && (
          <Button onClick={generate} loading={generating} variant="secondary">
            Regenerate prep
          </Button>
        )}
      </header>

      {error && <ErrorMessage error={error} title="Could not load interview prep" onRetry={load} />}

      {!prep && notFound === "analysis" && !error && (
        <EmptyState
          icon="📈"
          title="Run a readiness check first"
          description="Interview prep is built from a job's skill gaps, so a readiness analysis has to exist first."
          action={<LinkButton to={`/readiness/${id}`}>Run readiness analysis →</LinkButton>}
        />
      )}

      {!prep && notFound === "prep" && !error && (
        <EmptyState
          icon="🎤"
          title="No interview prep yet"
          description="Generate a set of practice questions built from your readiness analysis and your own resume/projects."
          action={
            <Button onClick={generate} loading={generating}>
              Generate prep
            </Button>
          }
        />
      )}

      {prep && (
        <>
          <section className="card p-6 sm:p-8">
            <ProgressBar
              completed={prep.completed_questions}
              total={prep.total_questions}
              percent={prep.progress_percent}
            />
          </section>

          {prep.questions.length === 0 ? (
            <EmptyState
              icon="🎤"
              title="No questions generated"
              description="There wasn't enough matched, missing, or resume/project evidence for this job to build practice questions from."
            />
          ) : (
            CATEGORY_ORDER.map((category) =>
              grouped[category].length ? (
                <section key={category} className="space-y-3">
                  <h2 className="text-lg font-semibold text-slate-900">
                    {CATEGORY_LABELS[category]}
                  </h2>
                  <ul className="space-y-3">
                    {grouped[category].map((question) => (
                      <QuestionCard
                        key={question.id}
                        question={question}
                        onToggle={toggleQuestion}
                        updating={updatingQuestionId === question.id}
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
