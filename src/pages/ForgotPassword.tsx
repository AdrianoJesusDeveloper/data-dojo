import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { api } from "@/lib/api";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    try {
      await api.post("/api/auth/password/reset/", { email });
      setMessage("Se existir uma conta com este e-mail, enviaremos as instruções de recuperação.");
    } catch (error: any) {
      setMessage(error?.response?.data?.detail || "Não foi possível solicitar a recuperação agora.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#0d0e12] p-8 text-white flex items-center justify-center">
      <form onSubmit={submit} className="w-full max-w-md rounded-xl border border-gray-800 bg-[#14161d] p-8">
        <h1 className="text-2xl font-bold">Recuperar senha</h1>
        <p className="mt-2 text-gray-400">Informe seu e-mail para receber as instruções.</p>
        <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="seu@email.com" className="mt-6 w-full rounded-md border border-gray-800 bg-[#1a1d26] p-3 text-white" />
        {message && <p className="mt-4 text-sm text-gray-300">{message}</p>}
        <button disabled={loading} className="mt-6 w-full rounded-md bg-[#ff3b30] px-5 py-3 font-bold disabled:opacity-50">{loading ? "Enviando..." : "Enviar instruções"}</button>
        <Link to="/login" className="mt-5 block text-center text-sm text-orange-400">Voltar para o login</Link>
      </form>
    </main>
  );
}
