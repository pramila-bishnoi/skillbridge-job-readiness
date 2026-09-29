import { Link } from "react-router-dom";

/**
 * Marks a page as part of the inherited HireMatch ATS rather than the
 * SkillBridge product, so a visitor who lands here directly (a shared link,
 * a bookmark) still understands they are in the secondary, compatibility
 * area rather than the primary student workflow.
 */
export function LegacyAtsBadge() {
  return (
    <p className="mb-3 inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-500">
      <span aria-hidden="true">🗂️</span>
      HireMatch ATS · legacy recruiting tool
      <span aria-hidden="true" className="text-slate-300">
        ·
      </span>
      <Link to="/dashboard" className="font-semibold text-brand-600 hover:underline">
        Go to SkillBridge
      </Link>
    </p>
  );
}
