import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import JobReadinessPage from "@/pages/JobReadinessPage";
import { readinessApi } from "@/api/readiness";
import { ApiError } from "@/api/client";
import { renderWithProviders } from "@/test/render";
import type { MatchAnalysisDetail } from "@/types/api";

vi.mock("@/api/readiness");
const mockedReadinessApi = vi.mocked(readinessApi);

function renderAt(route = "/readiness/5") {
  return renderWithProviders(
    <Routes>
      <Route path="/readiness/:jobProfileId" element={<JobReadinessPage />} />
    </Routes>,
    { route },
  );
}

const analysis: MatchAnalysisDetail = {
  id: 1,
  job_profile_id: 5,
  job_title: "Backend Engineer",
  readiness_score: 76,
  score_version: "v1",
  required_skill_coverage: 60,
  required_matched_count: 3,
  required_total_count: 5,
  preferred_skill_coverage: 50,
  preferred_matched_count: 1,
  preferred_total_count: 2,
  experience_score: 80,
  experience_evidence: "Detected 4 year(s) of experience against a 3-5 years requirement.",
  text_similarity_score: 42,
  text_similarity_terms: "python, fastapi",
  matched_skills: [
    {
      skill_id: 1,
      name: "Python",
      category: "language",
      requirement_type: "REQUIRED",
      gap_type: "MATCHED",
      importance: "LOW",
      evidence: "Found in your normalized skills.",
      related_to_skill_name: null,
    },
    {
      skill_id: 2,
      name: "Git",
      category: "tool",
      requirement_type: "PREFERRED",
      gap_type: "MATCHED",
      importance: "LOW",
      evidence: "Found in your normalized skills.",
      related_to_skill_name: null,
    },
  ],
  missing_skills: [
    {
      skill_id: 3,
      name: "Docker",
      category: "devops",
      requirement_type: "REQUIRED",
      gap_type: "MISSING_REQUIRED",
      importance: "HIGH",
      evidence: "Not found in your normalized skills; the job lists this as required.",
      related_to_skill_name: null,
    },
    {
      skill_id: 4,
      name: "Redis",
      category: "database",
      requirement_type: "PREFERRED",
      gap_type: "MISSING_PREFERRED",
      importance: "MEDIUM",
      evidence: "Not found in your normalized skills; the job lists this as preferred.",
      related_to_skill_name: null,
    },
  ],
  skill_gaps: [
    {
      skill_id: 3,
      name: "Docker",
      category: "devops",
      requirement_type: "REQUIRED",
      gap_type: "MISSING_REQUIRED",
      importance: "HIGH",
      evidence: "Not found in your normalized skills; the job lists this as required.",
      related_to_skill_name: null,
    },
    {
      skill_id: 4,
      name: "Redis",
      category: "database",
      requirement_type: "PREFERRED",
      gap_type: "MISSING_PREFERRED",
      importance: "MEDIUM",
      evidence: "Not found in your normalized skills; the job lists this as preferred.",
      related_to_skill_name: null,
    },
  ],
  created_at: "2026-09-28T10:00:00Z",
  updated_at: "2026-09-28T10:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("JobReadinessPage", () => {
  it("shows a prompt to run analysis when none exists yet", async () => {
    mockedReadinessApi.get.mockRejectedValue(
      new ApiError("not found", "MATCH_ANALYSIS_NOT_FOUND", 404),
    );
    renderAt();

    expect(
      await screen.findByText(/No readiness analysis yet/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run analysis" })).toBeInTheDocument();
  });

  it("renders the full readiness breakdown when an analysis exists", async () => {
    mockedReadinessApi.get.mockResolvedValue(analysis);
    renderAt();

    expect(await screen.findByText("Backend Engineer")).toBeInTheDocument();
    expect(screen.getByText("76%")).toBeInTheDocument();
    expect(screen.getByText("Why 76%?")).toBeInTheDocument();
    expect(screen.getByText("Required skill coverage · weighted 45%")).toBeInTheDocument();
    expect(screen.getByText("3/5 (60%)")).toBeInTheDocument();

    const dockerRows = screen.getAllByText("Docker");
    expect(dockerRows.length).toBeGreaterThan(0);
    expect(screen.getByText("HIGH")).toBeInTheDocument();
    expect(screen.getByText("MEDIUM")).toBeInTheDocument();
    expect(
      screen.getAllByText("Not found in your normalized skills; the job lists this as required.")
        .length,
    ).toBeGreaterThan(0);
  });

  it("runs a fresh analysis when the button is clicked", async () => {
    mockedReadinessApi.get.mockRejectedValue(
      new ApiError("not found", "MATCH_ANALYSIS_NOT_FOUND", 404),
    );
    mockedReadinessApi.analyze.mockResolvedValue(analysis);
    const user = userEvent.setup();
    renderAt();

    await screen.findByRole("button", { name: "Run analysis" });
    await user.click(screen.getByRole("button", { name: "Run analysis" }));

    await waitFor(() => expect(mockedReadinessApi.analyze).toHaveBeenCalledWith(5));
    expect(await screen.findByText("76%")).toBeInTheDocument();
  });
});
