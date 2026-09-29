import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SkillProgressPage from "@/pages/SkillProgressPage";
import { skillProgressApi } from "@/api/skillProgress";
import { studentApi } from "@/api/student";
import { renderWithProviders } from "@/test/render";
import type { SkillCatalogEntry, SkillProgressEntry } from "@/types/api";

vi.mock("@/api/skillProgress");
vi.mock("@/api/student");
const mockedSkillProgressApi = vi.mocked(skillProgressApi);
const mockedStudentApi = vi.mocked(studentApi);

const tracked: SkillProgressEntry[] = [
  {
    skill_id: 1,
    name: "Docker",
    category: "devops",
    status: "LEARNING",
    updated_at: "2026-09-29T10:00:00Z",
  },
];

const catalog: SkillCatalogEntry[] = [
  { skill_id: 1, name: "Docker", category: "devops" },
  { skill_id: 2, name: "Python", category: "language" },
  { skill_id: 3, name: "AWS", category: "cloud" },
];

beforeEach(() => {
  vi.clearAllMocks();
  mockedStudentApi.token.mockReturnValue("student-token");
  mockedSkillProgressApi.list.mockResolvedValue(tracked);
  mockedSkillProgressApi.listCatalog.mockResolvedValue(catalog);
});

describe("SkillProgressPage", () => {
  it("prompts to create a profile first when there is no student token", async () => {
    mockedStudentApi.token.mockReturnValue(null);
    renderWithProviders(<SkillProgressPage />);

    expect(
      await screen.findByText("Create a profile to track skill progress"),
    ).toBeInTheDocument();
    expect(mockedSkillProgressApi.list).not.toHaveBeenCalled();
  });

  it("renders tracked skills and excludes them from the add-skill dropdown", async () => {
    renderWithProviders(<SkillProgressPage />);

    expect(await screen.findByText("Docker")).toBeInTheDocument();
    expect(screen.getByText("Your tracked skills (1)")).toBeInTheDocument();

    const select = screen.getByRole("combobox", { name: "Skill" }) as HTMLSelectElement;
    const optionLabels = Array.from(select.options).map((o) => o.textContent);
    expect(optionLabels).toContain("Python");
    expect(optionLabels).toContain("AWS");
    expect(optionLabels).not.toContain("Docker");
  });

  it("updates a tracked skill's status", async () => {
    mockedSkillProgressApi.update.mockResolvedValue({
      ...tracked[0],
      status: "CONFIDENT",
      updated_at: "2026-09-29T11:00:00Z",
    });
    const user = userEvent.setup();
    renderWithProviders(<SkillProgressPage />);

    await screen.findByText("Docker");
    await user.selectOptions(screen.getByLabelText("Progress for Docker"), "CONFIDENT");

    await waitFor(() =>
      expect(mockedSkillProgressApi.update).toHaveBeenCalledWith(1, "CONFIDENT"),
    );
    await waitFor(() =>
      expect(screen.getAllByText("Confident").length).toBeGreaterThan(0),
    );
  });

  it("adds a new skill to track", async () => {
    mockedSkillProgressApi.update.mockResolvedValue({
      skill_id: 2,
      name: "Python",
      category: "language",
      status: "LEARNING",
      updated_at: "2026-09-29T11:00:00Z",
    });
    const user = userEvent.setup();
    renderWithProviders(<SkillProgressPage />);

    await screen.findByText("Docker");
    await user.selectOptions(screen.getByRole("combobox", { name: "Skill" }), "2");
    await user.click(screen.getByRole("button", { name: "Add" }));

    await waitFor(() => expect(mockedSkillProgressApi.update).toHaveBeenCalledWith(2, "LEARNING"));
    expect(await screen.findByText("Your tracked skills (2)")).toBeInTheDocument();
  });

  it("shows an empty message when nothing is tracked yet", async () => {
    mockedSkillProgressApi.list.mockResolvedValue([]);
    renderWithProviders(<SkillProgressPage />);

    expect(await screen.findByText(/Nothing tracked yet/i)).toBeInTheDocument();
  });
});
