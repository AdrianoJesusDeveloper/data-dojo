import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import type { ComponentPropsWithoutRef } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({ API_ORIGIN: "http://localhost:8000", api: { get: vi.fn() } }));

vi.mock("@/lib/dojo-store", () => ({
  useDojo: () => ({ state: { xp: 0, studentName: "Tester" } }),
  getCurrentBelt: () => ({ id: "white", name: "Faixa Branca", color: "#fff", kanji: "白" }),
  useHydrated: () => true,
}));

vi.mock("@tanstack/react-router", () => ({
  Link: (props: ComponentPropsWithoutRef<"a">) => <a {...props} />,
  useRouterState: () => "/",
  useNavigate: () => () => {},
}));

vi.mock("@/components/BeltBadge", () => ({
  BeltBadge: () => <div>Badge</div>,
  BeltProgress: () => <div>Progress</div>,
}));

import { DojoHeader } from "../components/DojoHeader";
import { useAuthStore } from "../lib/auth-store";

describe("DojoHeader smoke", () => {
  beforeEach(() => {
    useAuthStore.setState({
      token: "token",
      isAuthenticated: true,
      isStaff: false,
      isSuperuser: false,
      accessLoaded: true,
    });
  });

  it("renders without crashing and shows title", () => {
    render(<DojoHeader />);
    expect(screen.getByText(/Data Driven Dojô/i)).toBeInTheDocument();
  });

  it("hides every internal area from students", () => {
    render(<DojoHeader />);
    expect(screen.queryByText("Project Studio")).not.toBeInTheDocument();
    expect(screen.queryByText("Content Studio")).not.toBeInTheDocument();
    expect(screen.queryByText(/Command Center/)).not.toBeInTheDocument();
  });

  it("keeps every internal area visible for staff", () => {
    useAuthStore.setState({ isStaff: true, accessLoaded: true });
    render(<DojoHeader />);
    expect(screen.getByText("Project Studio")).toBeInTheDocument();
    expect(screen.getByText("Content Studio")).toBeInTheDocument();
    expect(screen.getByText(/Command Center/)).toBeInTheDocument();
  });
});
