import { useState } from "react";
import { useNavigate, createFileRoute, Link, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/login")({
  beforeLoad: () => {
    if (typeof window === "undefined") return;
    const isAuthenticated = !!window.localStorage.getItem("token");
    if (isAuthenticated) {
      throw redirect({ to: "/" });
    }
  },
  component: Login,
});

export function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    try {
      const response = await fetch("http://127.0.0.1:8000/api/auth/login/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: email,
          email: email,
          password: password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        const errorMsg = data.non_field_errors || data.detail || "Usuário ou senha incorretos.";
        throw new Error(Array.isArray(errorMsg) ? errorMsg[0] : errorMsg);
      }

      // Salva o token de sessão obtido do Django
      localStorage.setItem("token", data.key);

      // Envia o usuário autenticado para a Home protegida
      navigate({ to: "/" });
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Erro ao conectar ao servidor.");
      }
    }
  };

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        height: "100vh",
        backgroundColor: "#0A0A0A",
        color: "#fff",
        fontFamily: "sans-serif",
      }}
    >
      <form
        onSubmit={handleLogin}
        style={{
          width: "340px",
          padding: "40px",
          background: "#111",
          borderRadius: "8px",
          border: "1px solid #222",
          boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
        }}
      >
        <h2
          style={{
            marginBottom: "24px",
            textAlign: "center",
            color: "#fff",
            textTransform: "uppercase",
            letterSpacing: "1px",
          }}
        >
          Data Driven Dojo
        </h2>

        {error && (
          <p
            style={{
              color: "#ff4d4d",
              fontSize: "14px",
              marginBottom: "16px",
              textAlign: "center",
            }}
          >
            {error}
          </p>
        )}

        <div style={{ marginBottom: "16px" }}>
          <label style={{ display: "block", marginBottom: "6px", fontSize: "14px", color: "#aaa" }}>
            Usuário ou E-mail
          </label>
          <input
            type="text"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            placeholder="Ex: seuemail@exemplo.com"
            style={{
              width: "100%",
              padding: "12px",
              background: "#1A1A1A",
              border: "1px solid #333",
              borderRadius: "4px",
              color: "#fff",
              outline: "none",
            }}
          />
        </div>

        <div style={{ marginBottom: "24px" }}>
          <label style={{ display: "block", marginBottom: "6px", fontSize: "14px", color: "#aaa" }}>
            Senha
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            placeholder="••••••••"
            style={{
              width: "100%",
              padding: "12px",
              background: "#1A1A1A",
              border: "1px solid #333",
              borderRadius: "4px",
              color: "#fff",
              outline: "none",
            }}
          />
        </div>

        <button
          type="submit"
          style={{
            width: "100%",
            padding: "14px",
            background: "#E50914",
            border: "none",
            borderRadius: "4px",
            color: "#fff",
            fontWeight: "bold",
            fontSize: "16px",
            cursor: "pointer",
          }}
        >
          ENTRAR NO DOJO
        </button>

        <p style={{ textAlign: "center", fontSize: "14px", color: "#aaa", marginTop: "16px" }}>
          Novo por aqui?{" "}
          <Link
            to="/register"
            style={{ color: "#E50914", textDecoration: "none", fontWeight: "bold" }}
          >
            Crie uma conta
          </Link>
        </p>
      </form>
    </div>
  );
}
