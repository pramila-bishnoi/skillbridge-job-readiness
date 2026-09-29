/**
 * Interview-preparation calls (SkillBridge Phase 6). Same `studentApiClient`
 * as `api/readiness.ts`/`api/preparation.ts` — its own module because
 * interview prep is its own domain (docs/SKILLBRIDGE_ARCHITECTURE.md §5.3).
 */
import { studentApiClient } from "./client";
import type { InterviewPrepDetail } from "@/types/api";

const base = (jobProfileId: number) => `/student/jobs/${jobProfileId}/interview-prep`;

export const interviewPrepApi = {
  generate: (jobProfileId: number) =>
    studentApiClient
      .post<InterviewPrepDetail>(base(jobProfileId))
      .then((response) => response.data),
  get: (jobProfileId: number) =>
    studentApiClient
      .get<InterviewPrepDetail>(base(jobProfileId))
      .then((response) => response.data),
  updateQuestionCompleted: (jobProfileId: number, questionId: number, completed: boolean) =>
    studentApiClient
      .patch<InterviewPrepDetail>(`${base(jobProfileId)}/questions/${questionId}`, { completed })
      .then((response) => response.data),
};
