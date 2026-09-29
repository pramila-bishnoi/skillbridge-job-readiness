import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import { studentApi } from "@/api/student";
import { ApiError, toApiError } from "@/api/client";
import { Button } from "@/components/common/Button";
import { ErrorMessage } from "@/components/common/ErrorMessage";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { TextAreaField, TextField } from "@/components/common/FormField";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { titleCase } from "@/utils/format";
import type { StudentProfile, StudentProfilePayload, StudentSkill } from "@/types/api";

/** Groups normalized skills by category, categories sorted alphabetically so
 * the layout stays stable as new skills are added to a profile. */
function groupSkillsByCategory(skills: StudentSkill[]): [string, StudentSkill[]][] {
  const groups = new Map<string, StudentSkill[]>();
  for (const skill of skills) {
    const key = skill.category ?? "Other";
    const bucket = groups.get(key) ?? [];
    bucket.push(skill);
    groups.set(key, bucket);
  }
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
}

const EMPTY: StudentProfilePayload = {
  name: "",
  email: "",
  education: "",
  skills: "",
  projects: "",
  experience: "",
};

export default function StudentProfilePage() {
  useDocumentTitle("My profile");
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [values, setValues] = useState<StudentProfilePayload>(EMPTY);
  const [loading, setLoading] = useState(Boolean(studentApi.token()));
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!studentApi.token()) return;
    studentApi
      .getProfile()
      .then((next) => {
        setProfile(next);
        setValues({
          name: next.name,
          email: next.email,
          education: next.education ?? "",
          skills: next.skills ?? "",
          projects: next.projects ?? "",
          experience: next.experience ?? "",
        });
      })
      .catch((caught) => setError(toApiError(caught)))
      .finally(() => setLoading(false));
  }, []);

  const update = (key: keyof StudentProfilePayload, value: string) => {
    setValues((current) => ({ ...current, [key]: value }));
    setNotice("");
  };

  const create = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const created = await studentApi.createProfile(values);
      setProfile(created);
      setNotice(
        "Your profile is ready. Upload a resume to extract your skills.",
      );
    } catch (caught) {
      setError(toApiError(caught));
    } finally {
      setSaving(false);
    }
  };

  const save = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const updated = await studentApi.updateProfile({
        name: values.name,
        education: values.education,
        skills: values.skills,
        projects: values.projects,
        experience: values.experience,
      });
      setProfile(updated);
      setNotice("Profile saved.");
    } catch (caught) {
      setError(toApiError(caught));
    } finally {
      setSaving(false);
    }
  };

  const upload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setError(null);
    setUploading(true);
    try {
      const updated = await studentApi.uploadResume(file);
      setProfile(updated);
      setNotice("Resume analyzed. Your extracted skills are ready to review.");
    } catch (caught) {
      setError(toApiError(caught));
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };

  if (loading) return <LoadingSpinner label="Loading your profile…" />;

  return (
    <div className="mx-auto max-w-5xl space-y-8 px-4 py-10 sm:px-6">
      <header className="max-w-2xl">
        <p className="text-sm font-semibold uppercase tracking-wide text-brand-700">
          SkillBridge
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
          Your job-readiness profile
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-slate-600">
          Build your profile once, then use it to understand how your experience
          fits the roles you want.
        </p>
      </header>
      {error && (
        <ErrorMessage error={error} title="Could not update your profile" />
      )}
      {notice && (
        <p className="rounded-lg border border-brand-200 bg-brand-50 px-4 py-3 text-sm text-brand-800">
          {notice}
        </p>
      )}
      {!profile ? (
        <form onSubmit={create} className="card space-y-5 p-6 sm:p-8">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              Start your profile
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Your profile is scoped to the private access token issued here.
            </p>
          </div>
          <div className="grid gap-5 sm:grid-cols-2">
            <TextField
              label="Name"
              required
              value={values.name}
              onChange={(event) => update("name", event.target.value)}
            />
            <TextField
              label="Email address"
              required
              type="email"
              value={values.email}
              onChange={(event) => update("email", event.target.value)}
            />
          </div>
          <ProfileFields values={values} update={update} />
          <Button type="submit" loading={saving}>
            Create profile
          </Button>
        </form>
      ) : (
        <>
          <form onSubmit={save} className="card space-y-5 p-6 sm:p-8">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">
                  Profile details
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  Keep your education, projects, and experience current.
                </p>
              </div>
              <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700">
                Profile active
              </span>
            </div>
            <div className="grid gap-5 sm:grid-cols-2">
              <TextField
                label="Name"
                required
                value={values.name}
                onChange={(event) => update("name", event.target.value)}
              />
              <TextField label="Email address" value={values.email} disabled />
            </div>
            <ProfileFields values={values} update={update} />
            <div className="flex justify-end">
              <Button type="submit" loading={saving}>
                Save profile
              </Button>
            </div>
          </form>
          <section className="card p-6 sm:p-8">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">
                  Resume intelligence
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  Upload a PDF, DOC, or DOCX to extract a first skills profile.
                </p>
              </div>
              {profile.resume_uploaded && (
                <span className="text-sm font-medium text-emerald-600">
                  {profile.resume_filename}
                </span>
              )}
            </div>
            <label className="mt-5 block cursor-pointer rounded-lg border border-dashed border-brand-300 bg-brand-50/50 p-6 text-center transition hover:bg-brand-50">
              <span className="text-sm font-semibold text-brand-800">
                {uploading ? "Analyzing resume…" : "Choose a resume"}
              </span>
              <span className="mt-1 block text-xs text-slate-500">
                PDF, DOC, or DOCX up to 5 MB
              </span>
              <input
                className="sr-only"
                type="file"
                accept=".pdf,.doc,.docx"
                onChange={upload}
                disabled={uploading}
              />
            </label>
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-slate-900">
                Extracted skills
              </h3>
              {profile.extracted_skills.length ? (
                <div className="mt-3 space-y-4">
                  {groupSkillsByCategory(profile.extracted_skills).map(
                    ([category, skills]) => (
                      <div key={category}>
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          {titleCase(category)}
                        </p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {skills.map((skill) => (
                            <span
                              key={skill.skill_id}
                              title={`Detected from "${skill.matched_text}" in your resume`}
                              className="rounded-full bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-700"
                            >
                              {skill.name}
                            </span>
                          ))}
                        </div>
                      </div>
                    ),
                  )}
                </div>
              ) : (
                <p className="mt-2 text-sm text-slate-500">
                  Upload a resume to see skills found in the document.
                </p>
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function ProfileFields({
  values,
  update,
}: {
  values: StudentProfilePayload;
  update: (key: keyof StudentProfilePayload, value: string) => void;
}) {
  return (
    <div className="space-y-5">
      <TextAreaField
        label="Education"
        rows={3}
        placeholder="BSc Computer Science, 2024"
        value={values.education}
        onChange={(event) => update("education", event.target.value)}
      />
      <TextAreaField
        label="Skills"
        rows={3}
        placeholder="Python, communication, SQL…"
        hint="Add context alongside the skills extracted from your resume."
        value={values.skills}
        onChange={(event) => update("skills", event.target.value)}
      />
      <TextAreaField
        label="Projects"
        rows={4}
        placeholder="Project name, what you built, and the result"
        value={values.projects}
        onChange={(event) => update("projects", event.target.value)}
      />
      <TextAreaField
        label="Experience"
        rows={4}
        placeholder="Internships, volunteering, or work experience"
        value={values.experience}
        onChange={(event) => update("experience", event.target.value)}
      />
    </div>
  );
}
