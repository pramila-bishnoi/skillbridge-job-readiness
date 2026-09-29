/**
 * Job-comparison calls (SkillBridge Phase 7). Same `studentApiClient` as the
 * other SkillBridge modules — its own file because comparison is its own
 * domain (docs/SKILLBRIDGE_ARCHITECTURE.md §5.3).
 */
import { studentApiClient } from "./client";
import type { JobComparisonResult } from "@/types/api";

export const jobComparisonApi = {
  compare: (jobProfileIds: number[]) =>
    studentApiClient
      .post<JobComparisonResult>("/student/job-comparison", { job_profile_ids: jobProfileIds })
      .then((response) => response.data),
};
