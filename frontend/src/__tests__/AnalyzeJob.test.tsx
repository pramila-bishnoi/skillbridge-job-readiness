import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AnalyzeJobPage from "@/pages/AnalyzeJobPage";
import { jobAnalysisApi } from "@/api/jobAnalysis";
import { studentApi } from "@/api/student";
import { renderWithProviders } from "@/test/render";
import type { JobProfileDetail } from "@/types/api";

vi.mock("@/api/jobAnalysis");
vi.mock("@/api/student");
const mockedJobAnalysisApi = vi.mocked(jobAnalysisApi);
const mockedStudentApi = vi.mocked(studentApi);

const analysis: JobProfileDetail = {
  id: 1,
  title: "Backend Engineer",
  company: "Acme Corp",
  description: "Requirements:\n- Python\n- Docker\n\nPreferred:\n- AWS",
  experience_required: "3-5 years",
  experience_evidence: "3-5 years",
  required_skills: [
    {
      skill_id: 1,
      name: "Python",
      category: "language",
      matched_text: "Python",
      match_type: "CANONICAL_NAME",
    },
    {
      skill_id: 2,
      name: "Docker",
      category: "devops",
      matched_text: "Docker",
      match_type: "CANONICAL_NAME",
    },
  ],
  preferred_skills: [
    {
      skill_id: 3,
      name: "AWS",
      category: "cloud",
      matched_text: "AWS",
      match_type: "CANONICAL_NAME",
    },
  ],
  source_url: null,
  location: null,
  employment_type: null,
  compensation: null,
  posted_date: null,
  created_at: "2026-09-28T10:00:00Z",
  updated_at: "2026-09-28T10:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("AnalyzeJobPage", () => {
  it("prompts to create a profile first when there is no student token", async () => {
    mockedStudentApi.token.mockReturnValue(null);
    renderWithProviders(<AnalyzeJobPage />);

    expect(await screen.findByText("Create your profile first")).toBeInTheDocument();
    expect(mockedJobAnalysisApi.list).not.toHaveBeenCalled();
  });

  it("submits a job description and shows the structured analysis", async () => {
    mockedStudentApi.token.mockReturnValue("student-token");
    mockedJobAnalysisApi.list.mockResolvedValue([]);
    mockedJobAnalysisApi.create.mockResolvedValue(analysis);
    const user = userEvent.setup();
    renderWithProviders(<AnalyzeJobPage />);

    await user.type(
      screen.getByRole("textbox", { name: "Job title" }),
      "Backend Engineer",
    );
    await user.type(
      screen.getByRole("textbox", { name: "Job description" }),
      "Requirements: Python, Docker. Preferred: AWS.",
    );
    await user.click(screen.getByRole("button", { name: "Analyze" }));

    expect(await screen.findByText("Detected role")).toBeInTheDocument();
    expect(screen.getAllByText(/3-5 years/).length).toBeGreaterThan(0);
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("Docker")).toBeInTheDocument();
    expect(screen.getByText("AWS")).toBeInTheDocument();
    expect(mockedJobAnalysisApi.create).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Backend Engineer" }),
    );
  });

  it("loads a previously saved analysis when clicked", async () => {
    mockedStudentApi.token.mockReturnValue("student-token");
    mockedJobAnalysisApi.list.mockResolvedValue([
      {
        id: 1,
        title: "Backend Engineer",
        company: "Acme Corp",
        experience_required: "3-5 years",
        required_skill_count: 2,
        preferred_skill_count: 1,
        created_at: "2026-09-28T10:00:00Z",
        updated_at: "2026-09-28T10:00:00Z",
      },
    ]);
    mockedJobAnalysisApi.get.mockResolvedValue(analysis);
    const user = userEvent.setup();
    renderWithProviders(<AnalyzeJobPage />);

    const savedItem = await screen.findByText("Backend Engineer");
    await user.click(savedItem);

    await waitFor(() => expect(mockedJobAnalysisApi.get).toHaveBeenCalledWith(1));
    expect(await screen.findByText("Detected role")).toBeInTheDocument();
  });
});
