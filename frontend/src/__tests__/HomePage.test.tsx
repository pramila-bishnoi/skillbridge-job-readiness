import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import HomePage from "@/pages/HomePage";
import { studentApi } from "@/api/student";
import { renderWithProviders } from "@/test/render";

vi.mock("@/api/student");
const mockedStudentApi = vi.mocked(studentApi);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("HomePage", () => {
  it("invites a new visitor to get started", () => {
    mockedStudentApi.token.mockReturnValue(null);
    renderWithProviders(<HomePage />);

    expect(screen.getByRole("link", { name: "Get started" })).toHaveAttribute(
      "href",
      "/profile",
    );
  });

  it("sends a returning student straight to their dashboard", () => {
    mockedStudentApi.token.mockReturnValue("student-token");
    renderWithProviders(<HomePage />);

    expect(
      screen.getByRole("link", { name: "Go to your dashboard" }),
    ).toHaveAttribute("href", "/dashboard");
  });

  it("links every workflow step and keeps the ATS reachable without being primary", () => {
    mockedStudentApi.token.mockReturnValue(null);
    renderWithProviders(<HomePage />);

    expect(screen.getByRole("link", { name: /Build your profile/ })).toHaveAttribute(
      "href",
      "/profile",
    );
    expect(screen.getByRole("link", { name: "Browse open roles" })).toHaveAttribute(
      "href",
      "/jobs",
    );
    expect(screen.getByRole("link", { name: "sign in as a recruiter" })).toHaveAttribute(
      "href",
      "/admin/login",
    );
  });
});
