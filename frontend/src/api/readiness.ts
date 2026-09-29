/**
 * Job-readiness analysis calls (SkillBridge Phase 4). Same `studentApiClient`
 * as `api/student.ts`/`api/jobAnalysis.ts` — its own module because
 * readiness is its own domain (docs/SKILLBRIDGE_ARCHITECTURE.md §5.3).
 */
import { studentApiClient } from "./client";
import type { MatchAnalysisDetail, SkillGap } from "@/types/api";

const base = (jobProfileId: number) => `/student/jobs/${jobProfileId}/readiness`;

export const readinessApi = {
  analyze: (jobProfileId: number) =>
    studentApiClient
      .post<MatchAnalysisDetail>(base(jobProfileId))
      .then((response) => response.data),
  get: (jobProfileId: number) =>
    studentApiClient
      .get<MatchAnalysisDetail>(base(jobProfileId))
      .then((response) => response.data),
  getMatched: (jobProfileId: number) =>
    studentApiClient
      .get<SkillGap[]>(`${base(jobProfileId)}/matched`)
      .then((response) => response.data),
  getMissing: (jobProfileId: number) =>
    studentApiClient
      .get<SkillGap[]>(`${base(jobProfileId)}/missing`)
      .then((response) => response.data),
  getGaps: (jobProfileId: number) =>
    studentApiClient
      .get<SkillGap[]>(`${base(jobProfileId)}/gaps`)
      .then((response) => response.data),
};
