export function Footer() {
  return (
    <footer className="mt-16 border-t border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-8 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <p>
          <span className="font-semibold text-slate-700">SkillBridge</span>
          <span className="mx-2 hidden sm:inline">·</span>
          <span className="block sm:inline">
            An explainable job-readiness and skill-gap coach for students
          </span>
        </p>
        <p className="text-xs">
          Includes a separate legacy recruiting tool (HireMatch ATS).
          Candidate and job data shown here is fictional and used for
          demonstration.
        </p>
      </div>
    </footer>
  );
}
