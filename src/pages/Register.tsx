import { FormEvent, useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";

import bgTech from "../assets/plano_de_fundo_tecnologico.png";
import logoOficial from "../assets/logooicial.png";
import { api } from "../lib/api";

export default function Register() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password1, setPassword1] = useState("");
  const [password2, setPassword2] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (password1 !== password2) {
      toast.error("As senhas precisam ser iguais.");
      return;
    }

    setLoading(true);

    try {
      await api.post("/api/auth/registration/", {
        email,
        username,
        password1,
        password2,
      });

      toast.success("Cadastro realizado. Bem-vindo ao Dojô!");
      navigate({ to: "/login" });
    } catch (error) {
      const message =
        typeof error === "object" && error !== null && "response" in error
          ? ((error as { response?: { data?: { detail?: string } } }).response
              ?.data?.detail ?? "Não foi possível criar sua conta.")
          : "Não foi possível criar sua conta.";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main
      className="min-h-screen bg-background bg-cover bg-center px-4 py-10"
      style={{ backgroundImage: `url(${bgTech})` }}
    >
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-md items-center justify-center">
        <section className="w-full rounded-2xl border border-border bg-card/95 p-6 shadow-2xl backdrop-blur sm:p-8">
          <div className="mb-8 text-center">
            <img
              src={logoOficial}
              alt="Data Driven Dojô"
              className="mx-auto mb-5 h-20 w-auto object-contain"
            />
            <p className="mb-2 text-xs font-bold uppercase tracking-[0.3em] text-kaizen">
              Entre no Dojô
            </p>
            <h1 className="font-display text-3xl font-bold text-foreground">
              Criar conta
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Comece sua jornada de Determinação, Disciplina e Dedicação.
            </p>
          </div>

          <form className="space-y-4" onSubmit={handleSubmit}>
            <label className="block text-sm font-medium">
              Usuário
              <input
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
                autoComplete="username"
                className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-3 outline-none transition focus:border-primary"
              />
            </label>

            <label className="block text-sm font-medium">
              E-mail
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                autoComplete="email"
                className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-3 outline-none transition focus:border-primary"
              />
            </label>

            <label className="block text-sm font-medium">
              Senha
              <input
                type="password"
                value={password1}
                onChange={(event) => setPassword1(event.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
                className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-3 outline-none transition focus:border-primary"
              />
            </label>

            <label className="block text-sm font-medium">
              Confirmar senha
              <input
                type="password"
                value={password2}
                onChange={(event) => setPassword2(event.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
                className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-3 outline-none transition focus:border-primary"
              />
            </label>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-primary px-4 py-3 font-bold text-primary-foreground transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Criando conta..." : "Entrar no Dojô"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            Já possui uma conta?{" "}
            <Link to="/login" className="font-semibold text-kaizen hover:underline">
              Fazer login
            </Link>
          </p>
        </section>
      </div>
    </main>
  );
}
