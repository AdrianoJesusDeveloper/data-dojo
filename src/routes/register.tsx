import { useState } from "react";
import { useNavigate, Link, createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/register")({
  component: Register,
});

export function Register() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const navigate = useNavigate();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    try {
      const response = await fetch("http://127.0.0.1:8000/api/auth/registration/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: username,
          email: email,
          password1: password, // AJUSTE: Django espera password1
          password2: password, // AJUSTE: Django espera password2 para confirmação
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        // AJUSTE: Tratamento atualizado para capturar erros de password1 ou password2
        const errorMsg =
          data.username || data.email || data.password1 || data.password2 || "Erro ao cadastrar.";
        throw new Error(Array.isArray(errorMsg) ? errorMsg[0] : errorMsg);
      }

      setSuccess(true);
      setTimeout(() => {
        navigate({ to: "/login" });
      }, 2000);
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
        onSubmit={handleRegister}
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
          Criar Conta
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
        {success && (
          <p
            style={{
              color: "#4dff4d",
              fontSize: "14px",
              marginBottom: "16px",
              textAlign: "center",
            }}
          >
            Cadastro realizado! Redirecionando...
          </p>
        )}

        <div style={{ marginBottom: "16px" }}>
          <label style={{ display: "block", marginBottom: "6px", fontSize: "14px", color: "#aaa" }}>
            Nome de Usuário
          </label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            placeholder="Ex: adria_ninja"
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

        <div style={{ marginBottom: "16px" }}>
          <label style={{ display: "block", marginBottom: "6px", fontSize: "14px", color: "#aaa" }}>
            E-mail
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            placeholder="seuemail@exemplo.com"
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
            marginBottom: "16px",
          }}
        >
          CADASTRAR NO DOJO
        </button>

        <p style={{ textAlign: "center", fontSize: "14px", color: "#aaa" }}>
          Já tem conta?{" "}
          <Link
            to="/login"
            style={{ color: "#E50914", textDecoration: "none", fontWeight: "bold" }}
          >
            Faça Login
          </Link>
        </p>
      </form>
    </div>
  );
}
