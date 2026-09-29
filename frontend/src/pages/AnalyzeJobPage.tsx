import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { jobAnalysisApi } from "@/api/jobAnalysis";
import { studentApi } from "@/api/student";
import { ApiError, toApiError } from "@/api/client";
import { Button, LinkButton } from "@/components/common/Button";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorMessage } from "@/components/common/ErrorMessage";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { TextAreaField, TextField } from "@/components/common/FormField";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { classNames } from "@/utils/format";
import type {
  JobProfileCreatePayload,
  JobProfileDetail,
  JobProfileSummary,
  JobRequirementSkill,
  JobUrlImportPreview,
} from "@/types/api";

const EMPTY: JobProfileCreatePayload = { title: "", company: "", description: "" };

type EntryMode = "paste" | "url";

function SkillChips({ skills }: { skills: JobRequirementSkill[] }) {
  if (!skills.length) {
    return <p className="text-sm text-slate-500">None identified.</p>;
  }
  return (
    <div className="flex flex-wrap gap-2">
      {skills.map((skill) => (
        <span
          key={skill.skill_id}
          title={`Detected from "${skill.matched_text}" in the description`}
          className="rounded-full bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-700"
        >
          {skill.name}
        </span>
      ))}
    </div>
  );
}

function AnalysisResult({ analysis }: { analysis: JobProfileDetail }) {
  return (
    <section className="card space-y-6 p-6 sm:p-8">
      <div>
        <p className="text-sm font-semibold uppercase tracking-wide text-brand-700">
          Detected role
        </p>
        <h2 className="mt-1 text-xl font-bold text-slate-900">
          {analysis.title}
          {analysis.company && (
            <span className="font-normal text-slate-500"> · {analysis.company}</span>
          )}
        </h2>
      </div>

      <div>
        <p className="text-sm font-semibold text-slate-900">Experience requirement</p>
        <p className="mt-1 text-sm text-slate-600">
          {analysis.experience_required ? (
            <>
              {analysis.experience_required}{" "}
              <span
                className="text-xs text-slate-400"
                title={`Detected from "${analysis.experience_evidence}"`}
              >
                (detected)
              </span>
            </>
          ) : (
            "Not specified in the description."
          )}
        </p>
      </div>

      <div>
        <p className="text-sm font-semibold text-slate-900">Required skills</p>
        <div className="mt-2">
          <SkillChips skills={analysis.required_skills} />
        </div>
      </div>

      <div>
        <p className="text-sm font-semibold text-slate-900">Preferred skills</p>
        <div className="mt-2">
          <SkillChips skills={analysis.preferred_skills} />
        </div>
        {analysis.preferred_skills.length === 0 && (
          <p className="mt-1 text-xs text-slate-400">
            Shown only when a "Preferred" / "Nice to have" section can be reliably
            identified in the description.
          </p>
        )}
      </div>
    </section>
  );
}

function MetaRow({ label, value }: { label: string; value: string | null }) {
  if (!value) return null;
  return (
    <div className="flex justify-between gap-4 text-sm">
      <span className="text-slate-500">{label}</span>
      <span className="text-right font-medium text-slate-900">{value}</span>
    </div>
  );
}

/** Shown after a successful "Import from Job URL" fetch, before anything is
 * saved. Title/company/description are editable — extraction is best-effort
 * (especially the HTML fallback, which cannot always find a title), so the
 * student can fix them up here rather than starting over on the paste tab. */
function JobUrlPreviewPanel({
  preview,
  title,
  company,
  description,
  onTitleChange,
  onCompanyChange,
  onDescriptionChange,
  onSave,
  onDiscard,
  saving,
}: {
  preview: JobUrlImportPreview;
  title: string;
  company: string;
  description: string;
  onTitleChange: (value: string) => void;
  onCompanyChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onSave: () => void;
  onDiscard: () => void;
  saving: boolean;
}) {
  return (
    <section className="card space-y-6 p-6 sm:p-8">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-brand-700">
            Preview — nothing is saved yet
          </p>
          <p className="mt-1 break-all text-xs text-slate-500">
            Source: {preview.source_url}
          </p>
        </div>
        <span className="shrink-0 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
          {preview.extraction_method === "JSON_LD" ? "Structured data found" : "Page text only"}
        </span>
      </div>

      {preview.warnings.length > 0 && (
        <ul className="space-y-1 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
          {preview.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      )}

      <div className="grid gap-5 sm:grid-cols-2">
        <TextField label="Job title" required value={title} onChange={(e) => onTitleChange(e.target.value)} />
        <TextField label="Company" value={company} onChange={(e) => onCompanyChange(e.target.value)} />
      </div>

      <div className="space-y-1.5 rounded-lg bg-slate-50 p-4">
        <MetaRow label="Location" value={preview.location} />
        <MetaRow label="Employment type" value={preview.employment_type} />
        <MetaRow label="Compensation" value={preview.compensation} />
        <MetaRow label="Posted" value={preview.posted_date} />
        <MetaRow label="Experience" value={preview.experience_required} />
      </div>

      <div>
        <p className="text-sm font-semibold text-slate-900">Required skills</p>
        <div className="mt-2">
          <SkillChips skills={preview.required_skills} />
        </div>
      </div>
      <div>
        <p className="text-sm font-semibold text-slate-900">Preferred skills</p>
        <div className="mt-2">
          <SkillChips skills={preview.preferred_skills} />
        </div>
      </div>

      <TextAreaField
        label="Full description (used for the analysis — edit if needed)"
        rows={10}
        value={description}
        onChange={(e) => onDescriptionChange(e.target.value)}
      />

      <div className="flex flex-wrap gap-3">
        <Button onClick={onSave} loading={saving} disabled={title.trim().length < 2}>
          Save this job
        </Button>
        <Button variant="secondary" onClick={onDiscard} disabled={saving}>
          Discard
        </Button>
      </div>
    </section>
  );
}

export default function AnalyzeJobPage() {
  useDocumentTitle("Analyze a job");
  const [hasProfile] = useState(Boolean(studentApi.token()));
  const [mode, setMode] = useState<EntryMode>("paste");
  const [values, setValues] = useState<JobProfileCreatePayload>(EMPTY);
  const [saved, setSaved] = useState<JobProfileSummary[]>([]);
  const [analysis, setAnalysis] = useState<JobProfileDetail | null>(null);
  const [loadingList, setLoadingList] = useState(hasProfile);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  // "Import from Job URL"
  const [importUrl, setImportUrl] = useState("");
  const [importLoading, setImportLoading] = useState(false);
  const [importError, setImportError] = useState<ApiError | null>(null);
  const [preview, setPreview] = useState<JobUrlImportPreview | null>(null);
  const [previewTitle, setPreviewTitle] = useState("");
  const [previewCompany, setPreviewCompany] = useState("");
  const [previewDescription, setPreviewDescription] = useState("");

  useEffect(() => {
    if (!hasProfile) return;
    jobAnalysisApi
      .list()
      .then(setSaved)
      .catch((caught) => setError(toApiError(caught)))
      .finally(() => setLoadingList(false));
  }, [hasProfile]);

  const update = (key: keyof JobProfileCreatePayload, value: string) =>
    setValues((current) => ({ ...current, [key]: value }));

  const saveJobProfile = async (payload: JobProfileCreatePayload) => {
    const created = await jobAnalysisApi.create(payload);
    setAnalysis(created);
    setSaved((current) => [
      {
        id: created.id,
        title: created.title,
        company: created.company,
        experience_required: created.experience_required,
        required_skill_count: created.required_skills.length,
        preferred_skill_count: created.preferred_skills.length,
        created_at: created.created_at,
        updated_at: created.updated_at,
      },
      ...current,
    ]);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await saveJobProfile(values);
      setValues(EMPTY);
    } catch (caught) {
      setError(toApiError(caught));
    } finally {
      setSubmitting(false);
    }
  };

  const fetchPreview = async (event: FormEvent) => {
    event.preventDefault();
    setImportError(null);
    setPreview(null);
    setImportLoading(true);
    try {
      const result = await jobAnalysisApi.importFromUrl(importUrl.trim());
      setPreview(result);
      setPreviewTitle(result.title ?? "");
      setPreviewCompany(result.company ?? "");
      setPreviewDescription(result.description);
    } catch (caught) {
      setImportError(toApiError(caught));
    } finally {
      setImportLoading(false);
    }
  };

  const discardPreview = () => {
    setPreview(null);
    setImportUrl("");
    setImportError(null);
  };

  const savePreview = async () => {
    if (!preview) return;
    setError(null);
    setSubmitting(true);
    try {
      await saveJobProfile({
        title: previewTitle,
        company: previewCompany || null,
        description: previewDescription,
        source_url: preview.source_url,
        location: preview.location,
        employment_type: preview.employment_type,
        compensation: preview.compensation,
        posted_date: preview.posted_date,
      });
      discardPreview();
      setMode("paste");
    } catch (caught) {
      setError(toApiError(caught));
    } finally {
      setSubmitting(false);
    }
  };

  const openSaved = async (jobProfileId: number) => {
    setError(null);
    try {
      setAnalysis(await jobAnalysisApi.get(jobProfileId));
    } catch (caught) {
      setError(toApiError(caught));
    }
  };

  if (!hasProfile) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
        <EmptyState
          icon="📋"
          title="Create your profile first"
          description="Analyzing a job description is tied to your SkillBridge profile, so we can compare it against your skills later."
          action={<LinkButton to="/profile">Go to my profile</LinkButton>}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-8 px-4 py-10 sm:px-6">
      <header className="max-w-2xl">
        <p className="text-sm font-semibold uppercase tracking-wide text-brand-700">
          SkillBridge
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
          Analyze a job description
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-slate-600">
          Paste a job description to see its required skills, preferred
          skills, and experience requirement — extracted with the same rules
          used to read your resume, so both sides speak the same language.
        </p>
      </header>

      {error && <ErrorMessage error={error} title="Could not analyze this description" />}

      <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1 text-sm">
        <button
          type="button"
          onClick={() => setMode("paste")}
          className={classNames(
            "rounded-md px-3 py-1.5 font-medium transition",
            mode === "paste" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700",
          )}
        >
          Paste description
        </button>
        <button
          type="button"
          onClick={() => setMode("url")}
          className={classNames(
            "rounded-md px-3 py-1.5 font-medium transition",
            mode === "url" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700",
          )}
        >
          Import from Job URL
        </button>
      </div>

      <div className="grid gap-8 lg:grid-cols-2">
        {mode === "paste" ? (
          <form onSubmit={submit} className="card space-y-5 p-6 sm:p-8">
            <div className="grid gap-5 sm:grid-cols-2">
              <TextField
                label="Job title"
                required
                value={values.title}
                onChange={(event) => update("title", event.target.value)}
              />
              <TextField
                label="Company"
                value={values.company ?? ""}
                onChange={(event) => update("company", event.target.value)}
              />
            </div>
            <TextAreaField
              label="Job description"
              required
              rows={12}
              placeholder="Paste the full job description here…"
              hint="Include a “Requirements” and a “Preferred” section if the posting has them — that is how required and preferred skills are told apart."
              value={values.description}
              onChange={(event) => update("description", event.target.value)}
            />
            <Button type="submit" loading={submitting}>
              Analyze
            </Button>
          </form>
        ) : preview ? (
          <div className="lg:col-span-2">
            <JobUrlPreviewPanel
              preview={preview}
              title={previewTitle}
              company={previewCompany}
              description={previewDescription}
              onTitleChange={setPreviewTitle}
              onCompanyChange={setPreviewCompany}
              onDescriptionChange={setPreviewDescription}
              onSave={savePreview}
              onDiscard={discardPreview}
              saving={submitting}
            />
          </div>
        ) : (
          <form onSubmit={fetchPreview} className="card space-y-5 p-6 sm:p-8">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Import from a job posting URL</h2>
              <p className="mt-1 text-xs text-slate-500">
                Paste the link to a public job posting. We fetch the page, read its
                structured job data when the site publishes it, and show you a
                preview before anything is saved.
              </p>
            </div>
            <TextField
              label="Job posting URL"
              required
              type="url"
              placeholder="https://example.com/careers/backend-engineer"
              value={importUrl}
              onChange={(event) => setImportUrl(event.target.value)}
            />
            {importError && (
              <div className="space-y-2">
                <ErrorMessage error={importError} title="Could not import this URL" />
                <Button type="button" variant="secondary" size="sm" onClick={() => setMode("paste")}>
                  Paste the description manually instead
                </Button>
              </div>
            )}
            <Button type="submit" loading={importLoading}>
              Fetch &amp; preview
            </Button>
          </form>
        )}

        <div className="space-y-4">
          {analysis && <AnalysisResult analysis={analysis} />}

          <div>
            <h2 className="text-sm font-semibold text-slate-900">Previously analyzed</h2>
            {loadingList ? (
              <LoadingSpinner label="Loading saved analyses…" />
            ) : saved.length ? (
              <ul className="mt-3 space-y-2">
                {saved.map((item) => (
                  <li key={item.id} className="card px-4 py-3">
                    <button
                      type="button"
                      onClick={() => openSaved(item.id)}
                      className="block w-full text-left text-sm"
                    >
                      <span className="font-medium text-slate-900">{item.title}</span>
                      {item.company && (
                        <span className="text-slate-500"> · {item.company}</span>
                      )}
                      <span className="mt-1 block text-xs text-slate-500">
                        {item.required_skill_count} required · {item.preferred_skill_count}{" "}
                        preferred
                        {item.experience_required && ` · ${item.experience_required}`}
                      </span>
                    </button>
                    <Link
                      to={`/readiness/${item.id}`}
                      className="mt-2 inline-block text-xs font-medium text-brand-600 hover:underline"
                    >
                      Check readiness →
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-sm text-slate-500">
                Nothing saved yet — analyze a description to see it here.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
