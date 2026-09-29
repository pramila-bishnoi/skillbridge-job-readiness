import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import StudentProfilePage from "@/pages/StudentProfilePage";
import { studentApi } from "@/api/student";
import { renderWithProviders } from "@/test/render";
import type { StudentProfile, StudentSkill } from "@/types/api";

vi.mock("@/api/student");
const mockedStudentApi = vi.mocked(studentApi);

const extractedSkills: StudentSkill[] = [
  {
    skill_id: 1,
    name: "Python",
    category: "language",
    matched_text: "Python",
    match_type: "CANONICAL_NAME",
  },
  {
    skill_id: 2,
    name: "FastAPI",
    category: "framework",
    matched_text: "FastAPI",
    match_type: "CANONICAL_NAME",
  },
  {
    skill_id: 3,
    name: "PostgreSQL",
    category: "database",
    matched_text: "Postgres",
    match_type: "ALIAS",
  },
];

const profile: StudentProfile = {
  id: 1,
  name: "Jordan Ellis",
  email: "jordan.ellis@example.com",
  education: "BSc Computer Science",
  skills: "Communication",
  projects: "Campus event planner",
  experience: "Student developer intern",
  resume_uploaded: true,
  resume_filename: "jordan.docx",
  extracted_skills: extractedSkills,
  created_at: "2026-09-28T10:00:00Z",
  updated_at: "2026-09-28T10:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
  mockedStudentApi.token.mockReturnValue(null);
});

describe("StudentProfilePage", () => {
  it("creates a student profile and shows extracted skills", async () => {
    const user = userEvent.setup();
    mockedStudentApi.createProfile.mockResolvedValue(profile);
    renderWithProviders(<StudentProfilePage />);

    await user.type(
      screen.getByRole("textbox", { name: "Name" }),
      "Jordan Ellis",
    );
    await user.type(
      screen.getByRole("textbox", { name: "Email address" }),
      "jordan.ellis@example.com",
    );
    await user.click(screen.getByRole("button", { name: "Create profile" }));

    expect(await screen.findByText("Resume intelligence")).toBeInTheDocument();
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("FastAPI")).toBeInTheDocument();
    expect(mockedStudentApi.createProfile).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "Jordan Ellis",
        email: "jordan.ellis@example.com",
      }),
    );
  });

  it("loads an existing profile and uploads a resume", async () => {
    const user = userEvent.setup();
    mockedStudentApi.token.mockReturnValue("student-token");
    mockedStudentApi.getProfile.mockResolvedValue({
      ...profile,
      resume_uploaded: false,
      extracted_skills: [],
    });
    mockedStudentApi.uploadResume.mockResolvedValue(profile);
    renderWithProviders(<StudentProfilePage />);

    expect(await screen.findByText("Profile details")).toBeInTheDocument();
    await user.upload(
      screen.getByLabelText(/Choose a resume/i),
      new File(["resume"], "jordan.docx", {
        type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      }),
    );

    await waitFor(() =>
      expect(mockedStudentApi.uploadResume).toHaveBeenCalled(),
    );
    expect(await screen.findByText("Python")).toBeInTheDocument();
  });

  it("groups extracted skills by category and explains how each was found", async () => {
    mockedStudentApi.token.mockReturnValue("student-token");
    mockedStudentApi.getProfile.mockResolvedValue(profile);
    renderWithProviders(<StudentProfilePage />);

    expect(await screen.findByText("Extracted skills")).toBeInTheDocument();
    expect(screen.getByText("Language")).toBeInTheDocument();
    expect(screen.getByText("Framework")).toBeInTheDocument();
    expect(screen.getByText("Database")).toBeInTheDocument();

    const postgres = screen.getByText("PostgreSQL");
    expect(postgres).toHaveAttribute(
      "title",
      'Detected from "Postgres" in your resume',
    );
  });
});
