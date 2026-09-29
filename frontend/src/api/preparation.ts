/**
 * Preparation-plan calls (SkillBridge Phase 5). Same `studentApiClient` as
 * `api/readiness.ts` — its own module because preparation is its own domain
 * (docs/SKILLBRIDGE_ARCHITECTURE.md §5.3).
 */
import { studentApiClient } from "./client";
import type { PreparationItemStatus, PreparationPlanDetail } from "@/types/api";

const base = (jobProfileId: number) => `/student/jobs/${jobProfileId}/preparation`;

export const preparationApi = {
  generate: (jobProfileId: number) =>
    studentApiClient
      .post<PreparationPlanDetail>(base(jobProfileId))
      .then((response) => response.data),
  get: (jobProfileId: number) =>
    studentApiClient
      .get<PreparationPlanDetail>(base(jobProfileId))
      .then((response) => response.data),
  updateItemStatus: (jobProfileId: number, itemId: number, status: PreparationItemStatus) =>
    studentApiClient
      .patch<PreparationPlanDetail>(`${base(jobProfileId)}/items/${itemId}`, { status })
      .then((response) => response.data),
};
