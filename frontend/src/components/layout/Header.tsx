import { useState, type FocusEvent } from "react";
import { Link, NavLink } from "react-router-dom";
import { classNames } from "@/utils/format";

/** The SkillBridge student workflow — the only thing in the primary nav. */
const PRIMARY_LINKS = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/profile", label: "My Profile" },
  { to: "/analyze", label: "Analyze a Job" },
  { to: "/compare", label: "Compare Jobs" },
  { to: "/skill-progress", label: "Skill Progress" },
];

/** The inherited HireMatch ATS — kept fully working as a compatibility
 * surface, but reachable only through the separate "HireMatch ATS" menu
 * below, never mixed into the primary SkillBridge nav
 * (docs/SKILLBRIDGE_ARCHITECTURE.md §22, Stage 5). */
const ATS_LINKS = [
  { to: "/jobs", label: "Browse open roles" },
  { to: "/track", label: "Track an application" },
];

export function Header() {
  const [open, setOpen] = useState(false);
  const [atsMenuOpen, setAtsMenuOpen] = useState(false);

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    classNames(
      "rounded-lg px-3 py-2 text-sm font-medium transition",
      isActive
        ? "bg-brand-50 text-brand-700"
        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
    );

  const atsLinkClass = ({ isActive }: { isActive: boolean }) =>
    classNames(
      "block rounded-md px-3 py-2 text-sm transition",
      isActive
        ? "bg-slate-100 text-slate-900"
        : "text-slate-600 hover:bg-slate-50 hover:text-slate-900",
    );

  const closeAtsMenuOnBlur = (event: FocusEvent<HTMLDivElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node)) {
      setAtsMenuOpen(false);
    }
  };

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link
          to="/"
          className="flex items-center gap-2.5"
          onClick={() => setOpen(false)}
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-sm font-bold text-white">
            SB
          </span>
          <span className="hidden text-sm font-semibold leading-tight text-slate-900 sm:block">
            SkillBridge
            <span className="block text-xs font-normal text-slate-500">
              Job Readiness &amp; Skill-Gap Coach
            </span>
          </span>
        </Link>

        <nav
          className="hidden items-center gap-1 md:flex"
          aria-label="SkillBridge"
        >
          {PRIMARY_LINKS.map((link) => (
            <NavLink key={link.to} to={link.to} className={linkClass}>
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="hidden items-center gap-2 md:flex">
          <div
            className="relative"
            onBlur={closeAtsMenuOnBlur}
          >
            <button
              type="button"
              className="flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-500 transition hover:border-slate-300 hover:text-slate-700"
              aria-haspopup="true"
              aria-expanded={atsMenuOpen}
              onClick={() => setAtsMenuOpen((value) => !value)}
            >
              HireMatch ATS
              <svg
                className={classNames(
                  "h-3.5 w-3.5 transition-transform",
                  atsMenuOpen && "rotate-180",
                )}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="2"
                aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="m6 9 6 6 6-6" />
              </svg>
            </button>

            {atsMenuOpen && (
              <div
                className="absolute right-0 mt-2 w-60 rounded-lg border border-slate-200 bg-white p-1.5 shadow-lg"
                role="menu"
              >
                <p className="px-3 pb-1.5 pt-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                  Legacy recruiting tool
                </p>
                {ATS_LINKS.map((link) => (
                  <NavLink
                    key={link.to}
                    to={link.to}
                    className={atsLinkClass}
                    onClick={() => setAtsMenuOpen(false)}
                  >
                    {link.label}
                  </NavLink>
                ))}
                <Link
                  to="/admin/login"
                  className="block rounded-md px-3 py-2 text-sm text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
                  onClick={() => setAtsMenuOpen(false)}
                >
                  Recruiter sign in
                </Link>
              </div>
            )}
          </div>
        </div>

        <button
          type="button"
          className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 md:hidden"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
        >
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path
              strokeLinecap="round"
              d={open ? "M6 18 18 6M6 6l12 12" : "M4 7h16M4 12h16M4 17h16"}
            />
          </svg>
        </button>
      </div>

      {open && (
        <nav
          className="border-t border-slate-200 bg-white px-4 py-3 md:hidden"
          aria-label="Mobile"
        >
          <div className="flex flex-col gap-1">
            {PRIMARY_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={linkClass}
                onClick={() => setOpen(false)}
              >
                {link.label}
              </NavLink>
            ))}
          </div>
          <p className="mb-1 mt-4 px-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
            HireMatch ATS (legacy recruiting tool)
          </p>
          <div className="flex flex-col gap-1">
            {ATS_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={linkClass}
                onClick={() => setOpen(false)}
              >
                {link.label}
              </NavLink>
            ))}
            <NavLink
              to="/admin/login"
              className={linkClass}
              onClick={() => setOpen(false)}
            >
              Recruiter sign in
            </NavLink>
          </div>
        </nav>
      )}
    </header>
  );
}
