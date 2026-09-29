import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import PreparationPlanPage from "@/pages/PreparationPlanPage";
import { preparationApi } from "@/api/preparation";
import { ApiError } from "@/api/client";
import { renderWithProviders } from "@/test/render";
import type { PreparationPlanDetail } from "@/types/api";

vi.mock("@/api/preparation");
const mockedPreparationApi = vi.mocked(preparationApi);

function renderAt(route = "/preparation/5") {
  return renderWithProviders(
    <Routes>
      <Route path="/preparation/:jobProfileId" element={<PreparationPlanPage />} />
    </Routes>,
    { route },
  );
}

const plan: PreparationPlanDetail = {
  id: 1,
  job_profile_id: 5,
  job_title: "Backend Engineer",
  match_analysis_id: 1,
  readiness_score: 62.3,
  total_items: 3,
  completed_items: 0,
  in_progress_items: 0,
  not_started_items: 3,
  progress_percent: 0,
  items: [
    {
      id: 10,
      skill_id: 25,
      name: "Docker",
      category: "devops",
      requirement_type: "REQUIRED",
      gap_type: "MISSING_REQUIRED",
      priority: "HIGH",
      reason: '"Backend Engineer" lists Docker as required, and it was not found in your profile.',
      learning_focus: "Containers, images, Dockerfile, and basic deployment.",
      status: "NOT_STARTED",
    },
    {
      id: 11,
      skill_id: 13,
      name: "Redis",
      category: "database",
      requirement_type: "PREFERRED",
      gap_type: "MISSING_PREFERRED",
      priority: "MEDIUM",
      reason: '"Backend Engineer" lists Redis as preferred, and it was not found in your profile.',
      learning_focus: "Key-value basics and caching patterns.",
      status: "NOT_STARTED",
    },
    {
      id: 12,
      skill_id: 1,
      name: "Python",
      category: "language",
      requirement_type: "REQUIRED",
      gap_type: "RELATED",
      priority: "LOW",
      reason: '"Backend Engineer" asks for Python. Your profile shows Django, which is related.',
      learning_focus: "Core syntax and data structures.",
      status: "NOT_STARTED",
    },
  ],
  created_at: "2026-09-29T10:00:00Z",
  updated_at: "2026-09-29T10:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("PreparationPlanPage", () => {
  it("prompts to run readiness first when no analysis exists", async () => {
    mockedPreparationApi.get.mockRejectedValue(
      new ApiError("not found", "MATCH_ANALYSIS_NOT_FOUND", 404),
    );
    renderAt();

    expect(
      await screen.findByText(/Run a readiness check first/i),
    ).toBeInTheDocument();
  });

  it("prompts to generate a plan when an analysis exists but no plan yet", async () => {
    mockedPreparationApi.get.mockRejectedValue(
      new ApiError("not found", "PREPARATION_PLAN_NOT_FOUND", 404),
    );
    renderAt();

    expect(
      await screen.findByText(/No preparation plan yet/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate plan" })).toBeInTheDocument();
  });

  it("renders the plan grouped by priority with reason and learning focus", async () => {
    mockedPreparationApi.get.mockResolvedValue(plan);
    renderAt();

    expect(await screen.findByText("Backend Engineer")).toBeInTheDocument();
    expect(screen.getByText("0%")).toBeInTheDocument();
    expect(screen.getByText("High priority")).toBeInTheDocument();
    expect(screen.getByText("Medium priority")).toBeInTheDocument();
    expect(screen.getByText("Low priority")).toBeInTheDocument();
    expect(screen.getByText(/Dockerfile/)).toBeInTheDocument();
    expect(screen.getByText(/lists Docker as required/)).toBeInTheDocument();
  });

  it("updates an item's status and refreshes progress", async () => {
    mockedPreparationApi.get.mockResolvedValue(plan);
    mockedPreparationApi.updateItemStatus.mockResolvedValue({
      ...plan,
      completed_items: 1,
      not_started_items: 2,
      progress_percent: 33.3,
      items: plan.items.map((item) =>
        item.id === 10 ? { ...item, status: "COMPLETED" } : item,
      ),
    });
    const user = userEvent.setup();
    renderAt();

    await screen.findByText("Backend Engineer");
    await user.selectOptions(screen.getByLabelText("Status for Docker"), "COMPLETED");

    await waitFor(() =>
      expect(mockedPreparationApi.updateItemStatus).toHaveBeenCalledWith(5, 10, "COMPLETED"),
    );
    expect(await screen.findByText("33.3%")).toBeInTheDocument();
  });

  it("generates a plan when the button is clicked", async () => {
    mockedPreparationApi.get.mockRejectedValue(
      new ApiError("not found", "PREPARATION_PLAN_NOT_FOUND", 404),
    );
    mockedPreparationApi.generate.mockResolvedValue(plan);
    const user = userEvent.setup();
    renderAt();

    await screen.findByRole("button", { name: "Generate plan" });
    await user.click(screen.getByRole("button", { name: "Generate plan" }));

    await waitFor(() => expect(mockedPreparationApi.generate).toHaveBeenCalledWith(5));
    expect(await screen.findByText("High priority")).toBeInTheDocument();
  });
});
