import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";

const { post } = vi.hoisted(() => ({ post: vi.fn() }));

vi.mock("@/lib/api", () => ({
  api: { post },
}));

import { AIChat } from "@/components/ai/AIChat";

describe("AIChat", () => {
  it("omits empty conversation credentials when starting a conversation", async () => {
    post.mockResolvedValueOnce({
      data: { conversation_id: 1, message: "Olá!" },
    });
    render(<AIChat />);

    fireEvent.change(screen.getByLabelText("Mensagem para o agente de IA"), {
      target: { value: "oi me responde" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/api/ai/chat/", {
        mentor: "dojo_ai",
        message: "oi me responde",
      }),
    );
  });
});
