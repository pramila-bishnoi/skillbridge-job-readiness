import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Header } from "@/components/layout/Header";
import { renderWithProviders } from "@/test/render";

describe("Header", () => {
  it("shows only SkillBridge links in the primary nav", () => {
    renderWithProviders(<Header />);

    const primaryNav = screen.getByRole("navigation", { name: "SkillBridge" });
    expect(within(primaryNav).getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    expect(within(primaryNav).getByRole("link", { name: "My Profile" })).toBeInTheDocument();
    expect(within(primaryNav).getByRole("link", { name: "Compare Jobs" })).toBeInTheDocument();
    expect(within(primaryNav).getByRole("link", { name: "Skill Progress" })).toBeInTheDocument();

    // The ATS links are not directly in the primary nav.
    expect(
      within(primaryNav).queryByRole("link", { name: /Browse open roles/i }),
    ).not.toBeInTheDocument();
  });

  it("keeps the ATS reachable behind a separate, clearly-labeled menu", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Header />);

    const toggle = screen.getByRole("button", { name: /HireMatch ATS/i });
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    expect(screen.getByRole("link", { name: "Browse open roles" })).toHaveAttribute(
      "href",
      "/jobs",
    );
    expect(screen.getByRole("link", { name: "Track an application" })).toHaveAttribute(
      "href",
      "/track",
    );
    expect(screen.getByRole("link", { name: "Recruiter sign in" })).toHaveAttribute(
      "href",
      "/admin/login",
    );
  });
});
