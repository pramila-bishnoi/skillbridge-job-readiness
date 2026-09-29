/**
 * Skill-progress calls (SkillBridge Phase 7). Same `studentApiClient` as the
 * other SkillBridge modules.
 */
import { studentApiClient } from "./client";
import type { SkillCatalogEntry, SkillProgressEntry, SkillProgressStatus } from "@/types/api";

export const skillProgressApi = {
  list: () =>
    studentApiClient
      .get<SkillProgressEntry[]>("/student/skill-progress")
      .then((response) => response.data),
  listCatalog: () =>
    studentApiClient
      .get<SkillCatalogEntry[]>("/student/skill-progress/catalog")
      .then((response) => response.data),
  update: (skillId: number, status: SkillProgressStatus) =>
    studentApiClient
      .patch<SkillProgressEntry>(`/student/skill-progress/${skillId}`, { status })
      .then((response) => response.data),
};
