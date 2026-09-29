import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import InterviewPrepPage from "@/pages/InterviewPrepPage";
import { interviewPrepApi } from "@/api/interviewPrep";
import { ApiError } from "@/api/client";
import { renderWithProviders } from "@/test/render";
import type { InterviewPrepDetail } from "@/types/api";

vi.mock("@/api/interviewPrep");
const mockedInterviewPrepApi = vi.mocked(interviewPrepApi);

function renderAt(route = "/interview-prep/5") {
  return renderWithProviders(
    <Routes>
      <Route path="/interview-prep/:jobProfileId" element={<InterviewPrepPage />} />
    </Routes>,
    { route },
  );
}

const prep: InterviewPrepDetail = {
  job_profile_id: 5,
  job_title: "Backend Engineer",
  match_analysis_id: 1,
  total_questions: 3,
  completed_questions: 0,
  progress_percent: 0,
  questions: [
    {
      id: 20,
      question:
        "You listed Python on your profile, and this role calls for it — walk me through a specific way you've used Python.",
      category: "TECHNICAL",
      related_skill_name: "Python",
      difficulty: "HARD",
      reason: "Python is a required skill for this role, and your profile shows it.",
      completed: false,
    },
    {
      id: 21,
      question: "This role expects familiarity with Docker. What do you understand about Docker so far?",
      category: "SKILL_GAP",
      related_skill_name: "Docker",
      difficulty: "MEDIUM",
      reason: "Docker is a required skill for this role and was not found in your profile.",
      completed: false,
    },
    {
      id: 22,
      question:
        'Your profile mentions this project: "Built an ESP32-based home automation system." — walk me through what you built.',
      category: "RESUME_PROJECT",
      related_skill_name: null,
      difficulty: "MEDIUM",
      reason: "Taken directly from the Projects section of your profile.",
      completed: false,
    },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("InterviewPrepPage", () => {
  it("prompts to run readiness first when no analysis exists", async () => {
    mockedInterviewPrepApi.get.mockRejectedValue(
      new ApiError("not found", "MATCH_ANALYSIS_NOT_FOUND", 404),
    );
    renderAt();

    expect(
      await screen.findByText(/Run a readiness check first/i),
    ).toBeInTheDocument();
  });

  it("prompts to generate prep when an analysis exists but no prep yet", async () => {
    mockedInterviewPrepApi.get.mockRejectedValue(
      new ApiError("not found", "INTERVIEW_PREP_NOT_FOUND", 404),
    );
    renderAt();

    expect(
      await screen.findByText(/No interview prep yet/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate prep" })).toBeInTheDocument();
  });

  it("renders questions grouped by category with the ESP32 project quoted verbatim", async () => {
    mockedInterviewPrepApi.get.mockResolvedValue(prep);
    renderAt();

    expect(await screen.findByText("Backend Engineer")).toBeInTheDocument();
    expect(screen.getByText("Technical")).toBeInTheDocument();
    expect(screen.getByText("Skill Gap")).toBeInTheDocument();
    expect(screen.getByText("Resume & Projects")).toBeInTheDocument();
    expect(screen.getByText(/ESP32/)).toBeInTheDocument();
    expect(screen.getAllByText("Python").length).toBeGreaterThan(0);
  });

  it("toggles a question completed and refreshes progress", async () => {
    mockedInterviewPrepApi.get.mockResolvedValue(prep);
    mockedInterviewPrepApi.updateQuestionCompleted.mockResolvedValue({
      ...prep,
      completed_questions: 1,
      progress_percent: 33.3,
      questions: prep.questions.map((q) => (q.id === 20 ? { ...q, completed: true } : q)),
    });
    const user = userEvent.setup();
    renderAt();

    await screen.findByText("Backend Engineer");
    const checkbox = screen.getByLabelText(/Mark reviewed.*walk me through a specific way/i);
    await user.click(checkbox);

    await waitFor(() =>
      expect(mockedInterviewPrepApi.updateQuestionCompleted).toHaveBeenCalledWith(5, 20, true),
    );
    expect(await screen.findByText("33.3%")).toBeInTheDocument();
  });

  it("generates prep when the button is clicked", async () => {
    mockedInterviewPrepApi.get.mockRejectedValue(
      new ApiError("not found", "INTERVIEW_PREP_NOT_FOUND", 404),
    );
    mockedInterviewPrepApi.generate.mockResolvedValue(prep);
    const user = userEvent.setup();
    renderAt();

    await screen.findByRole("button", { name: "Generate prep" });
    await user.click(screen.getByRole("button", { name: "Generate prep" }));

    await waitFor(() => expect(mockedInterviewPrepApi.generate).toHaveBeenCalledWith(5));
    expect(await screen.findByText("Technical")).toBeInTheDocument();
  });
});
