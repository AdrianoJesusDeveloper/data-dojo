import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import type { ComponentPropsWithoutRef } from "react";
import { describe, expect, it, vi } from "vitest";

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

describe("DojoHeader smoke", () => {
  it("renders without crashing and shows title", () => {
    render(<DojoHeader />);
    expect(screen.getByText(/Data Driven Dojô/i)).toBeInTheDocument();
  });
});
