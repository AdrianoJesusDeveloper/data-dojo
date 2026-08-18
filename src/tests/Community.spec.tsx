import { fireEvent, render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/dojo-store", () => ({
  useDojo: () => ({ state: { xp: 0, studentName: "Tester" } }),
  getCurrentBelt: () => ({ id: "white", name: "Faixa Branca", color: "#fff", kanji: "白" }),
  useHydrated: () => true,
  BELTS: [
    { id: "white", color: "#fff", name: "Faixa Branca", kanji: "白" },
    { id: "yellow", color: "#FFEB99", name: "Faixa Amarela", kanji: "黄" },
    { id: "green", color: "#99FF99", name: "Faixa Verde", kanji: "緑" },
    { id: "black", color: "#000000", name: "Faixa Preta", kanji: "黒" },
  ],
}));

vi.mock("@/components/DojoHeader", () => ({
  DojoHeader: () => <div>HeaderMock</div>,
}));

import Community from "../pages/Community";

describe("Community smoke", () => {
  it("renders composer and allows typing", () => {
    render(<Community />);
    expect(screen.getByText(/Comunidade/i)).toBeInTheDocument();

    const textarea = screen.getByPlaceholderText(/Compartilhe sua conquista/i);
    fireEvent.change(textarea, { target: { value: "Olá comunidade" } });
    expect((textarea as HTMLTextAreaElement).value).toBe("Olá comunidade");
  });
});
