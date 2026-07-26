import { useState } from "react";
import { useNavigate, Link, createFileRoute } from "@tanstack/react-router";

import bgTech from "../assets/plano_de_fundo_tecnologico.png";
import logoOficial from "../assets/logooicial.png"; 

export const Route = createFileRoute("/register")({
  component: Register,
});

function Register() {
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
          password1: password, 
          password2: password, 
        }),
      });

      if (!response.ok) {
        const data = await response.json();
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
        width: "100vw",
        backgroundImage: `linear-gradient(rgba(0, 0, 0, 0.65), rgba(0, 0, 0, 0.65)), url(${bgTech})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundRepeat: "no-repeat",
        color: "#fff",
        fontFamily: "sans-serif",
        position: "relative",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: "24px",
          left: "24px",
          display: "flex",
          alignItems: "center",
        }}
      >
        <img
          src={logoOficial}
          alt="Data Driven Dojo Logo"
          style={{
            height: "60px",
            width: "auto",
            borderRadius: "8px",
            boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
          }}
        />
      </div>

      <form
        onSubmit={handleRegister}
        style={{
          width: "360px",
          padding: "40px",
          background: "rgba(17, 17, 17, 0.85)",
          backdropFilter: "blur(8px)",
          borderRadius: "12px",
          border: "1px solid rgba(255, 255, 255, 0.1)",
          boxShadow: "0 8px 32px rgba(0,0,0,0.7)",
        }}
      >
        <h2
          style={{
            marginBottom: "24px",
            textAlign: "center",
            color: "#fff",
            textTransform: "uppercase",
            letterSpacing: "1.5px",
            fontSize: "22px",
            fontWeight: "bold",
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
              background: "rgba(255, 77, 77, 0.1)",
              padding: "8px",
              borderRadius: "4px",
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
              background: "rgba(77, 255, 77, 0.1)",
              padding: "8px",
              borderRadius: "4px",
            }}
          >
            Cadastro realizado! Redirecionando...
          </p>
        )}

        <div style={{ display: "block", marginBottom: "18px" }}>
          <label style={{ display: "block", marginBottom: "6px", fontSize: "14px", color: "#ccc" }}>
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
              background: "rgba(26, 26, 26, 0.8)",
              border: "1px solid #444",
              borderRadius: "6px",
              color: "#fff",
              outline: "none",
            }}
          />
        </div>

        <div style={{ display: "block", marginBottom: "18px" }}>
          <label style={{ display: "block", marginBottom: "6px", fontSize: "14px", color: "#ccc" }}>
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
              background: "rgba(26, 26, 26, 0.8)",
              border: "1px solid #444",
              borderRadius: "6px",
              color: "#fff",
              outline: "none",
            }}
          />
        </div>

        <div style={{ marginBottom: "28px" }}>
          <label style={{ display: "block", marginBottom: "6px", fontSize: "14px", color: "#ccc" }}>
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
              background: "rgba(26, 26, 26, 0.8)",
              border: "1px solid #444",
              borderRadius: "6px",
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
            background: "#0066cc",
            border: "none",
            borderRadius: "6px",
            color: "#fff",
            fontWeight: "bold",
            fontSize: "16px",
            cursor: "pointer",
            letterSpacing: "0.5px",
            transition: "background 0.2s",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "#0052a3")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "#0066cc")}
        >
          CADASTRAR NO DOJO
        </button>

        <p style={{ textAlign: "center", fontSize: "14px", color: "#bbb", marginTop: "20px" }}>
          Já tem conta?{" "}
          <Link
            to="/login"
            style={{ color: "#0066cc", textDecoration: "none", fontWeight: "bold" }}
          >
            Faça Login
          </Link>
        </p>
      </form>
    </div>
  );
}