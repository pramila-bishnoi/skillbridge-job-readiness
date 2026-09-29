/**
 * Saved job-analysis calls (SkillBridge Phase 3). Uses the same
 * `studentApiClient` as `api/student.ts` — a separate module because job
 * analysis is its own domain, not an extension of the profile API
 * (docs/SKILLBRIDGE_ARCHITECTURE.md §5.3).
 */
import { studentApiClient } from "./client";
import type {
  JobProfileCreatePayload,
  JobProfileDetail,
  JobProfileSummary,
  JobUrlImportPreview,
} from "@/types/api";

export const jobAnalysisApi = {
  create: (payload: JobProfileCreatePayload) =>
    studentApiClient
      .post<JobProfileDetail>("/student/jobs", payload)
      .then((response) => response.data),
  list: () =>
    studentApiClient
      .get<JobProfileSummary[]>("/student/jobs")
      .then((response) => response.data),
  get: (jobProfileId: number) =>
    studentApiClient
      .get<JobProfileDetail>(`/student/jobs/${jobProfileId}`)
      .then((response) => response.data),
  reanalyze: (jobProfileId: number) =>
    studentApiClient
      .post<JobProfileDetail>(`/student/jobs/${jobProfileId}/analyze`)
      .then((response) => response.data),
  /** Fetches and extracts a public job-posting URL. Nothing is saved — the
   * student reviews the preview, then confirms via `create()` above. */
  importFromUrl: (url: string) =>
    studentApiClient
      .post<JobUrlImportPreview>("/student/jobs/import-url", { url })
      .then((response) => response.data),
};
