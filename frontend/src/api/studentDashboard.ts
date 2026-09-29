/**
 * Student dashboard-summary calls (SkillBridge Phase 7). Not to be confused
 * with `api/admin.ts`'s recruiter dashboard stats — a different audience and
 * a different endpoint (`/student/dashboard` vs `/admin/stats`).
 */
import { studentApiClient } from "./client";
import type { StudentDashboardSummary } from "@/types/api";

export const studentDashboardApi = {
  get: () =>
    studentApiClient
      .get<StudentDashboardSummary>("/student/dashboard")
      .then((response) => response.data),
};
