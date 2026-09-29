import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import JobComparisonPage from "@/pages/JobComparisonPage";
import { jobAnalysisApi } from "@/api/jobAnalysis";
import { jobComparisonApi } from "@/api/jobComparison";
import { studentApi } from "@/api/student";
import { ApiError } from "@/api/client";
import { renderWithProviders } from "@/test/render";
import type { JobComparisonResult, JobProfileSummary } from "@/types/api";

vi.mock("@/api/jobAnalysis");
vi.mock("@/api/jobComparison");
vi.mock("@/api/student");
const mockedJobAnalysisApi = vi.mocked(jobAnalysisApi);
const mockedJobComparisonApi = vi.mocked(jobComparisonApi);
const mockedStudentApi = vi.mocked(studentApi);

const savedJobs: JobProfileSummary[] = [
  {
    id: 1,
    title: "Backend Engineer",
    company: "Acme Corp",
    experience_required: "3-5 years",
    required_skill_count: 3,
    preferred_skill_count: 1,
    created_at: "2026-09-29T10:00:00Z",
    updated_at: "2026-09-29T10:00:00Z",
  },
  {
    id: 2,
    title: "Data Engineer",
    company: "Beta Inc",
    experience_required: null,
    required_skill_count: 2,
    preferred_skill_count: 0,
    created_at: "2026-09-29T10:00:00Z",
    updated_at: "2026-09-29T10:00:00Z",
  },
];

const comparisonResult: JobComparisonResult = {
  jobs: [
    {
      job_profile_id: 1,
      title: "Backend Engineer",
      company: "Acme Corp",
      readiness_score: 70,
      required_skill_coverage: 66.7,
      preferred_skill_coverage: 100,
      matched_skills: ["Python"],
      missing_skills: ["Docker"],
      unique_missing_skills: ["Docker"],
    },
    {
      job_profile_id: 2,
      title: "Data Engineer",
      company: "Beta Inc",
      readiness_score: 50,
      required_skill_coverage: 50,
      preferred_skill_coverage: 0,
      matched_skills: ["Python"],
      missing_skills: ["SQL"],
      unique_missing_skills: ["SQL"],
    },
  ],
  common_skills: ["Python"],
  common_missing_skills: [],
};

beforeEach(() => {
  vi.clearAllMocks();
  mockedStudentApi.token.mockReturnValue("student-token");
  mockedJobAnalysisApi.list.mockResolvedValue(savedJobs);
});

describe("JobComparisonPage", () => {
  it("prompts to create a profile first when there is no student token", async () => {
    mockedStudentApi.token.mockReturnValue(null);
    renderWithProviders(<JobComparisonPage />);

    expect(
      await screen.findByText("Create a profile to compare jobs"),
    ).toBeInTheDocument();
    expect(mockedJobAnalysisApi.list).not.toHaveBeenCalled();
  });

  it("shows an empty state when the student has no saved jobs", async () => {
    mockedJobAnalysisApi.list.mockResolvedValue([]);
    renderWithProviders(<JobComparisonPage />);

    expect(await screen.findByText("No saved jobs yet")).toBeInTheDocument();
  });

  it("disables Compare until at least two jobs are selected", async () => {
    const user = userEvent.setup();
    renderWithProviders(<JobComparisonPage />);

    await screen.findByText("Backend Engineer");
    expect(screen.getByRole("button", { name: "Compare" })).toBeDisabled();

    await user.click(screen.getByRole("checkbox", { name: /Backend Engineer/i }));
    expect(screen.getByRole("button", { name: "Compare" })).toBeDisabled();

    await user.click(screen.getByRole("checkbox", { name: /Data Engineer/i }));
    expect(screen.getByRole("button", { name: "Compare" })).not.toBeDisabled();
  });

  it("compares selected jobs and shows readiness side by side", async () => {
    mockedJobComparisonApi.compare.mockResolvedValue(comparisonResult);
    const user = userEvent.setup();
    renderWithProviders(<JobComparisonPage />);

    await screen.findByText("Backend Engineer");
    await user.click(screen.getByRole("checkbox", { name: /Backend Engineer/i }));
    await user.click(screen.getByRole("checkbox", { name: /Data Engineer/i }));
    await user.click(screen.getByRole("button", { name: "Compare" }));

    await waitFor(() =>
      expect(mockedJobComparisonApi.compare).toHaveBeenCalledWith([1, 2]),
    );
    expect(await screen.findByText("Readiness side by side")).toBeInTheDocument();
    expect(screen.getByText("70%")).toBeInTheDocument();
    expect(screen.getAllByText("50%").length).toBeGreaterThan(0);
  });

  it("shows a hint when a selected job has not been analyzed yet", async () => {
    mockedJobComparisonApi.compare.mockRejectedValue(
      new ApiError("not analyzed", "JOBS_NOT_ANALYZED", 409),
    );
    const user = userEvent.setup();
    renderWithProviders(<JobComparisonPage />);

    await screen.findByText("Backend Engineer");
    await user.click(screen.getByRole("checkbox", { name: /Backend Engineer/i }));
    await user.click(screen.getByRole("checkbox", { name: /Data Engineer/i }));
    await user.click(screen.getByRole("button", { name: "Compare" }));

    expect(
      await screen.findByText(/Run a readiness analysis for every selected job first/i),
    ).toBeInTheDocument();
  });
});
