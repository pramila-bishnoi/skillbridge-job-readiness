import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import StudentDashboardPage from "@/pages/StudentDashboardPage";
import { studentApi } from "@/api/student";
import { studentDashboardApi } from "@/api/studentDashboard";
import { renderWithProviders } from "@/test/render";
import type { StudentDashboardSummary } from "@/types/api";

vi.mock("@/api/student");
vi.mock("@/api/studentDashboard");
const mockedStudentApi = vi.mocked(studentApi);
const mockedStudentDashboardApi = vi.mocked(studentDashboardApi);

const summary: StudentDashboardSummary = {
  tracked_skills_count: 3,
  not_started_count: 1,
  learning_count: 1,
  practiced_count: 0,
  confident_count: 1,
  analyzed_jobs_count: 2,
  average_readiness_score: 61.5,
  best_readiness_job: {
    job_profile_id: 5,
    title: "Backend Engineer",
    readiness_score: 70,
  },
  recent_skill_progress: [
    {
      skill_id: 1,
      name: "Docker",
      category: "devops",
      status: "LEARNING",
      updated_at: "2026-09-29T10:00:00Z",
    },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
  mockedStudentApi.token.mockReturnValue("student-token");
});

describe("StudentDashboardPage", () => {
  it("prompts to create a profile first when there is no student token", async () => {
    mockedStudentApi.token.mockReturnValue(null);
    renderWithProviders(<StudentDashboardPage />);

    expect(await screen.findByText("Welcome to SkillBridge")).toBeInTheDocument();
    expect(mockedStudentDashboardApi.get).not.toHaveBeenCalled();
  });

  it("renders headline stats and the best-readiness job", async () => {
    mockedStudentDashboardApi.get.mockResolvedValue(summary);
    renderWithProviders(<StudentDashboardPage />);

    expect(await screen.findByText("Your dashboard")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument(); // tracked skills
    expect(screen.getByText("2")).toBeInTheDocument(); // analyzed jobs
    expect(screen.getByText("61.5%")).toBeInTheDocument();
    expect(screen.getByText("Backend Engineer")).toBeInTheDocument();
    expect(screen.getByText(/70%/)).toBeInTheDocument();
  });

  it("shows a fallback message when nothing has been analyzed yet", async () => {
    mockedStudentDashboardApi.get.mockResolvedValue({
      ...summary,
      analyzed_jobs_count: 0,
      average_readiness_score: null,
      best_readiness_job: null,
      recent_skill_progress: [],
    });
    renderWithProviders(<StudentDashboardPage />);

    expect(
      await screen.findByText(/Analyze a job and run a readiness check/i),
    ).toBeInTheDocument();
  });
});
