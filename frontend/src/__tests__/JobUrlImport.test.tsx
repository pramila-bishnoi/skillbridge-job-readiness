import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AnalyzeJobPage from "@/pages/AnalyzeJobPage";
import { jobAnalysisApi } from "@/api/jobAnalysis";
import { studentApi } from "@/api/student";
import { ApiError } from "@/api/client";
import { renderWithProviders } from "@/test/render";
import type { JobProfileDetail, JobUrlImportPreview } from "@/types/api";

vi.mock("@/api/jobAnalysis");
vi.mock("@/api/student");
const mockedJobAnalysisApi = vi.mocked(jobAnalysisApi);
const mockedStudentApi = vi.mocked(studentApi);

const preview: JobUrlImportPreview = {
  source_url: "https://boards.example.com/jobs/42",
  extraction_method: "JSON_LD",
  title: "Backend Engineer",
  company: "Acme Corp",
  location: "Bengaluru, IN",
  employment_type: "Full-time",
  compensation: "$120,000–$150,000/year",
  posted_date: "2026-09-01",
  description: "Requirements:\nPython\nFastAPI\n\nPreferred:\nDocker",
  experience_required: "3-5 years",
  experience_evidence: "3-5 years",
  required_skills: [
    { skill_id: 1, name: "Python", category: "language", matched_text: "Python", match_type: "CANONICAL_NAME" },
    { skill_id: 4, name: "FastAPI", category: "framework", matched_text: "FastAPI", match_type: "CANONICAL_NAME" },
  ],
  preferred_skills: [
    { skill_id: 5, name: "Docker", category: "devops", matched_text: "Docker", match_type: "CANONICAL_NAME" },
  ],
  warnings: [],
};

const created: JobProfileDetail = {
  id: 9,
  title: "Backend Engineer",
  company: "Acme Corp",
  description: preview.description,
  experience_required: "3-5 years",
  experience_evidence: "3-5 years",
  required_skills: preview.required_skills,
  preferred_skills: preview.preferred_skills,
  source_url: preview.source_url,
  location: preview.location,
  employment_type: preview.employment_type,
  compensation: preview.compensation,
  posted_date: preview.posted_date,
  created_at: "2026-09-29T10:00:00Z",
  updated_at: "2026-09-29T10:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
  mockedStudentApi.token.mockReturnValue("student-token");
  mockedJobAnalysisApi.list.mockResolvedValue([]);
});

describe("AnalyzeJobPage — Import from Job URL", () => {
  it("fetches a preview and shows the extracted fields without saving anything", async () => {
    mockedJobAnalysisApi.importFromUrl.mockResolvedValue(preview);
    const user = userEvent.setup();
    renderWithProviders(<AnalyzeJobPage />);

    await user.click(screen.getByRole("button", { name: "Import from Job URL" }));
    await user.type(
      screen.getByRole("textbox", { name: "Job posting URL" }),
      "https://boards.example.com/jobs/42",
    );
    await user.click(screen.getByRole("button", { name: /Fetch & preview/ }));

    expect(await screen.findByText("Preview — nothing is saved yet")).toBeInTheDocument();
    expect(mockedJobAnalysisApi.importFromUrl).toHaveBeenCalledWith(
      "https://boards.example.com/jobs/42",
    );
    expect(screen.getByDisplayValue("Backend Engineer")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Acme Corp")).toBeInTheDocument();
    expect(screen.getByText("Bengaluru, IN")).toBeInTheDocument();
    expect(screen.getByText("Full-time")).toBeInTheDocument();
    expect(screen.getByText("$120,000–$150,000/year")).toBeInTheDocument();
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("Docker")).toBeInTheDocument();
    expect(mockedJobAnalysisApi.create).not.toHaveBeenCalled();
  });

  it("saves the previewed job through the existing create call when confirmed", async () => {
    mockedJobAnalysisApi.importFromUrl.mockResolvedValue(preview);
    mockedJobAnalysisApi.create.mockResolvedValue(created);
    const user = userEvent.setup();
    renderWithProviders(<AnalyzeJobPage />);

    await user.click(screen.getByRole("button", { name: "Import from Job URL" }));
    await user.type(
      screen.getByRole("textbox", { name: "Job posting URL" }),
      "https://boards.example.com/jobs/42",
    );
    await user.click(screen.getByRole("button", { name: /Fetch & preview/ }));
    await screen.findByText("Preview — nothing is saved yet");

    await user.click(screen.getByRole("button", { name: "Save this job" }));

    await waitFor(() =>
      expect(mockedJobAnalysisApi.create).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Backend Engineer",
          company: "Acme Corp",
          source_url: "https://boards.example.com/jobs/42",
          location: "Bengaluru, IN",
          employment_type: "Full-time",
        }),
      ),
    );
    expect(await screen.findByText("Detected role")).toBeInTheDocument();
  });

  it("shows a clear error and a manual-paste fallback when extraction fails", async () => {
    mockedJobAnalysisApi.importFromUrl.mockRejectedValue(
      new ApiError(
        "Could not find a job description on that page. Paste it manually instead.",
        "JOB_URL_EXTRACTION_FAILED",
        422,
      ),
    );
    const user = userEvent.setup();
    renderWithProviders(<AnalyzeJobPage />);

    await user.click(screen.getByRole("button", { name: "Import from Job URL" }));
    await user.type(
      screen.getByRole("textbox", { name: "Job posting URL" }),
      "https://example.com/careers",
    );
    await user.click(screen.getByRole("button", { name: /Fetch & preview/ }));

    expect(
      await screen.findByText(/Could not find a job description on that page/),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Paste the description manually instead" }));
    expect(screen.getByRole("textbox", { name: "Job description" })).toBeInTheDocument();
  });

  it("shows a clear error when the URL is blocked as unsafe", async () => {
    mockedJobAnalysisApi.importFromUrl.mockRejectedValue(
      new ApiError(
        "That URL points to a private or internal address and cannot be fetched.",
        "JOB_URL_BLOCKED",
        403,
      ),
    );
    const user = userEvent.setup();
    renderWithProviders(<AnalyzeJobPage />);

    await user.click(screen.getByRole("button", { name: "Import from Job URL" }));
    await user.type(
      screen.getByRole("textbox", { name: "Job posting URL" }),
      "http://169.254.169.254/",
    );
    await user.click(screen.getByRole("button", { name: /Fetch & preview/ }));

    expect(
      await screen.findByText(/private or internal address/),
    ).toBeInTheDocument();
  });

  it("lets the student discard a preview and start over", async () => {
    mockedJobAnalysisApi.importFromUrl.mockResolvedValue(preview);
    const user = userEvent.setup();
    renderWithProviders(<AnalyzeJobPage />);

    await user.click(screen.getByRole("button", { name: "Import from Job URL" }));
    await user.type(
      screen.getByRole("textbox", { name: "Job posting URL" }),
      "https://boards.example.com/jobs/42",
    );
    await user.click(screen.getByRole("button", { name: /Fetch & preview/ }));
    await screen.findByText("Preview — nothing is saved yet");

    await user.click(screen.getByRole("button", { name: "Discard" }));
    expect(screen.getByRole("textbox", { name: "Job posting URL" })).toHaveValue("");
  });
});
