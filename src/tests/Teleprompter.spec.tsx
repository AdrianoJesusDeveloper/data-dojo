import { act, fireEvent, render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Teleprompter } from "@/components/content-studio/Teleprompter";
import { downloadFilename } from "@/lib/download-filename";

afterEach(() => { vi.unstubAllGlobals(); });

describe("Teleprompter", () => {
  it("scrolls, pauses, moves, restarts and changes font and speed", () => {
    let callback: FrameRequestCallback = () => {};
    const cancel = vi.fn();
    vi.stubGlobal("requestAnimationFrame", vi.fn((fn: FrameRequestCallback) => { callback = fn; return 1; }));
    vi.stubGlobal("cancelAnimationFrame", cancel);
    render(<Teleprompter title="Aula gravável" text="Primeiro, formule sua hipótese." status="REVIEW" onClose={() => {}} />);
    expect(screen.getByText(/Ensaio de roteiro/)).toBeInTheDocument();
    const viewport = screen.getByLabelText("Texto do teleprompter");
    Object.defineProperties(viewport, { scrollHeight: { value: 2000 }, clientHeight: { value: 500 } });
    fireEvent.click(screen.getByRole("button", { name: "Iniciar" }));
    act(() => callback(0));
    act(() => callback(100));
    expect(viewport.scrollTop).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Pausar" }));
    expect(cancel).toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Avançar" }));
    expect(viewport.scrollTop).toBeGreaterThan(300);
    fireEvent.click(screen.getByRole("button", { name: "Voltar" }));
    expect(viewport.scrollTop).toBeLessThan(10);
    fireEvent.click(screen.getByRole("button", { name: "Reiniciar" }));
    expect(viewport.scrollTop).toBe(0);
    fireEvent.click(screen.getByRole("button", { name: "Aumentar fonte" }));
    expect(viewport).toHaveStyle({ fontSize: "44px" });
    fireEvent.click(screen.getByRole("button", { name: "Diminuir fonte" }));
    expect(viewport).toHaveStyle({ fontSize: "40px" });
    fireEvent.change(screen.getByLabelText("Velocidade"), { target: { value: "60" } });
    expect(screen.getByText(/60 px\/s/)).toBeInTheDocument();
  });

  it("reports unavailable fullscreen without losing the script", async () => {
    render(<Teleprompter title="Vídeo" text="Texto aprovado." status="APPROVED" onClose={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "Tela cheia" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Tela cheia indisponível");
    expect(screen.getByText("Texto aprovado.")).toBeInTheDocument();
  });
});

describe("downloadFilename", () => {
  it("uses backend UTF-8, quoted and unquoted names safely", () => {
    expect(downloadFilename("attachment; filename*=UTF-8''aula%20pr%C3%A1tica.pdf", "fallback")).toBe("aula prática.pdf");
    expect(downloadFilename('attachment; filename="plano.docx"; size=123', "fallback")).toBe("plano.docx");
    expect(downloadFilename('attachment; filename=plano.pptx; size=123', "fallback")).toBe("plano.pptx");
    expect(downloadFilename(undefined, "fallback.pdf")).toBe("fallback.pdf");
  });
});
