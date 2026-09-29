import { Link } from "react-router-dom";
import { studentApi } from "@/api/student";
import { LinkButton } from "@/components/common/Button";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

const STEPS = [
  {
    step: "1",
    title: "Build your profile",
    body: "Upload a resume and we extract your skills against a canonical catalog — no guessing, every match is explainable.",
    to: "/profile",
  },
  {
    step: "2",
    title: "Analyze a job",
    body: "Paste a job description and see it broken into required skills, preferred skills, and an experience requirement.",
    to: "/analyze",
  },
  {
    step: "3",
    title: "See your readiness",
    body: "A component-by-component readiness score, plus exactly which required and preferred skills you're missing.",
    to: "/analyze",
  },
  {
    step: "4",
    title: "Prepare",
    body: "A prioritized study plan and role-specific interview questions, generated from your own gaps — nothing invented.",
    to: "/analyze",
  },
];

export default function HomePage() {
  useDocumentTitle();
  const hasProfile = Boolean(studentApi.token());

  return (
    <>
      <section className="bg-gradient-to-b from-brand-50 to-slate-50">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-24">
          <div className="max-w-2xl">
            <p className="text-sm font-semibold uppercase tracking-wide text-brand-700">
              SkillBridge
            </p>
            <h1 className="mt-3 text-3xl font-bold leading-tight tracking-tight text-slate-900 sm:text-5xl">
              Know exactly how ready you are for the job you want
            </h1>
            <p className="mt-5 text-base leading-relaxed text-slate-600 sm:text-lg">
              Upload your resume, paste a job description, and get an
              explainable readiness score — with a prioritized list of the
              skills to close the gap, and interview questions built from
              your own profile. Deterministic rules only: every result
              traces back to something you actually wrote.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <LinkButton to={hasProfile ? "/dashboard" : "/profile"} size="lg">
                {hasProfile ? "Go to your dashboard" : "Get started"}
              </LinkButton>
              <LinkButton to="/analyze" variant="secondary" size="lg">
                Analyze a job
              </LinkButton>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <h2 className="text-xl font-semibold text-slate-900">How it works</h2>
        <div className="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((item) => (
            <Link key={item.step} to={item.to} className="card p-5 transition hover:border-brand-300 hover:shadow-md">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-white">
                {item.step}
              </span>
              <h3 className="mt-4 text-base font-semibold text-slate-900">
                {item.title}
              </h3>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-600">
                {item.body}
              </p>
            </Link>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 pb-16 sm:px-6">
        <div className="card p-6 text-sm text-slate-600 sm:p-8">
          <p>
            SkillBridge also includes a legacy recruiting tool — a careers
            portal and admin console — kept as a separate, compatible
            workspace and not part of the SkillBridge student experience.{" "}
            <Link to="/jobs" className="font-medium text-brand-600 hover:underline">
              Browse open roles
            </Link>{" "}
            or{" "}
            <Link to="/admin/login" className="font-medium text-brand-600 hover:underline">
              sign in as a recruiter
            </Link>
            .
          </p>
        </div>
      </section>
    </>
  );
}
