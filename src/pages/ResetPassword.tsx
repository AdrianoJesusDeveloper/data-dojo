import { useState } from "react";
import { Link, useSearch } from "@tanstack/react-router";
import { api } from "@/lib/api";

export default function ResetPassword() {
  const search = useSearch({ from: "/reset-password" });

  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();

    setLoading(true);
    setMessage("");
    setSuccess(false);

    try {
      await api.post("/api/auth/password-reset/confirm/", {
        uid: search.uid,
        token: search.token,
        password,
        password_confirmation: passwordConfirmation,
      });

      setSuccess(true);
      setMessage("Senha redefinida com sucesso. Você já pode entrar.");
    } catch (error: any) {
      setMessage(
        error?.response?.data?.detail ||
          error?.response?.data?.password?.[0] ||
          "Não foi possível redefinir sua senha."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#0d0e12] p-8 text-white flex items-center justify-center">
      <form
        onSubmit={submit}
        className="w-full max-w-md rounded-xl border border-gray-800 bg-[#14161d] p-8"
      >
        <h1 className="text-2xl font-bold">Criar nova senha</h1>

        <p className="mt-2 text-gray-400">
          Digite sua nova senha abaixo.
        </p>

        <input
          type="password"
          required
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Nova senha"
          className="mt-6 w-full rounded-md border border-gray-800 bg-[#1a1d26] p-3 text-white"
        />

        <input
          type="password"
          required
          minLength={8}
          value={passwordConfirmation}
          onChange={(e) => setPasswordConfirmation(e.target.value)}
          placeholder="Confirme a nova senha"
          className="mt-4 w-full rounded-md border border-gray-800 bg-[#1a1d26] p-3 text-white"
        />

        {message && (
          <p className="mt-4 text-sm text-gray-300">
            {message}
          </p>
        )}

        {!success && (
          <button
            disabled={loading}
            className="mt-6 w-full rounded-md bg-[#ff3b30] px-5 py-3 font-bold disabled:opacity-50"
          >
            {loading ? "Salvando..." : "Redefinir senha"}
          </button>
        )}

        {success && (
          <Link
            to="/login"
            className="mt-6 block w-full rounded-md bg-[#ff3b30] px-5 py-3 text-center font-bold"
          >
            Ir para o login
          </Link>
        )}
      </form>
    </main>
  );
}
