import { useEffect } from "react";

const SUFFIX = "SkillBridge – Job Readiness & Skill-Gap Coach";

export function useDocumentTitle(title?: string) {
  useEffect(() => {
    document.title = title ? `${title} · ${SUFFIX}` : SUFFIX;
  }, [title]);
}
