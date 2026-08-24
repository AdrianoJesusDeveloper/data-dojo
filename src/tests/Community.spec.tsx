import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
import { useAuthStore } from "@/lib/auth-store";

const post = {
  id: 7, content: "Post original", created_at: "2026-08-24T12:00:00Z", updated_at: "2026-08-24T12:00:00Z",
  user: { id: 1, username: "Tester" }, likes_count: 0, liked_by_me: false, comments_count: 1, is_owner: true,
  comments: [{ id: 9, content: "Comentário original", created_at: "2026-08-24T12:01:00Z", user: { id: 1, username: "Tester" }, likes_count: 0, is_owner: true }],
};

function response(data: unknown = {}, status = 200) {
  return Promise.resolve(new Response(status === 204 ? null : JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } }));
}

describe("Community smoke", () => {
  it("renders composer and allows typing", () => {
    render(<Community />);
    expect(screen.getByText(/Comunidade/i)).toBeInTheDocument();

    const textarea = screen.getByPlaceholderText(/Compartilhe sua conquista/i);
    fireEvent.change(textarea, { target: { value: "Olá comunidade" } });
    expect((textarea as HTMLTextAreaElement).value).toBe("Olá comunidade");
  });

  it("uses the persisted authentication token when loading posts", async () => {
    localStorage.setItem("ddj-auth", JSON.stringify({ state: { token: "token-dojo", isAuthenticated: true }, version: 0 }));
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }));

    render(<Community />);

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ headers: { Authorization: "Token token-dojo" } });
    fetchMock.mockRestore();
    localStorage.clear();
  });

  it("publishes, likes, comments, edits and deletes through the API", async () => {
    useAuthStore.setState({ token: "token-dojo", isAuthenticated: true });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      const url = String(input);
      const method = init?.method || "GET";
      if (url.endsWith("/like/")) return response({ likes_count: 1, liked_by_me: true });
      if (method === "DELETE") return response({}, 204);
      if (method === "GET") return response([post]);
      return response(post, method === "POST" ? 201 : 200);
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<Community />);
    await screen.findByText("Post original");

    fireEvent.change(screen.getByPlaceholderText(/Compartilhe sua conquista/i), { target: { value: "Novo post" } });
    fireEvent.click(screen.getByRole("button", { name: "Publicar" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/api/community/posts/"), expect.objectContaining({ method: "POST" })));

    fireEvent.click(screen.getAllByRole("button", { name: /0/ })[0]);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/posts/7/like/"), expect.objectContaining({ method: "POST" })));

    fireEvent.change(screen.getByPlaceholderText("Escreva uma resposta..."), { target: { value: "Nova resposta" } });
    fireEvent.click(screen.getByRole("button", { name: "Responder" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/community/comments/"), expect.objectContaining({ method: "POST" })));

    fireEvent.click(screen.getAllByRole("button", { name: "Editar" })[0]);
    fireEvent.change(screen.getByDisplayValue("Post original"), { target: { value: "Post editado" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/posts/7/"), expect.objectContaining({ method: "PATCH" })));

    fireEvent.click(screen.getAllByRole("button", { name: "Excluir" })[1]);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/comments/9/"), expect.objectContaining({ method: "DELETE" })));
    fireEvent.click(screen.getByRole("button", { name: "Excluir" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/posts/7/"), expect.objectContaining({ method: "DELETE" })));

    fetchMock.mockRestore();
    useAuthStore.getState().logout();
  });
});
