import { useState } from "react";
import {
  useNavigate,
  Link,
  createFileRoute,
} from "@tanstack/react-router";

import { api } from "../lib/api";

import bgTech from "../assets/plano_de_fundo_tecnologico.png";
import logoOficial from "../assets/logooicial.png";

export const Route = createFileRoute("/register")({
  component: Register,
});

export default function Register() {
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleRegister = async (
    e: React.FormEvent<HTMLFormElement>
  ) => {
    e.preventDefault();

    setError("");
    setSuccess(false);

    try {
      await api.post("/api/auth/registration/", {
        username,
        email,
        password1: password,
        password2: password,
      });

      setSuccess(true);

      setTimeout(() => {
        navigate({ to: "/login" });
      }, 2000);
    } catch (err: any) {
      if (err.response?.data) {
        const data = err.response.data;

        const errorMessage =
          data.username?.[0] ||
          data.email?.[0] ||
          data.password1?.[0] ||
          data.password2?.[0] ||
          data.detail ||
          "Erro ao realizar o cadastro.";

        setError(errorMessage);
      } else {
        setError("Não foi possível conectar ao servidor.");
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
        backgroundImage: `linear-gradient(rgba(0,0,0,.65), rgba(0,0,0,.65)), url(${bgTech})`,
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
          top: 24,
          left: 24,
        }}
      >
        <img
          src={logoOficial}
          alt="Data Driven Dojo"
          style={{
            height: 60,
            borderRadius: 8,
            boxShadow: "0 4px 12px rgba(0,0,0,.35)",
          }}
        />
      </div>

      <form
        onSubmit={handleRegister}
        style={{
          width: 380,
          padding: 40,
          background: "rgba(17,17,17,.88)",
          borderRadius: 12,
          backdropFilter: "blur(8px)",
          border: "1px solid rgba(255,255,255,.08)",
          boxShadow: "0 8px 30px rgba(0,0,0,.6)",
        }}
      >
        <h2
          style={{
            textAlign: "center",
            marginBottom: 30,
            letterSpacing: 2,
          }}
        >
          Criar Conta
        </h2>

        {error && (
          <div
            style={{
              background: "#3b1111",
              color: "#ff8080",
              padding: 12,
              marginBottom: 20,
              borderRadius: 6,
              textAlign: "center",
            }}
          >
            {error}
          </div>
        )}

        {success && (
          <div
            style={{
              background: "#153d19",
              color: "#77ff77",
              padding: 12,
              marginBottom: 20,
              borderRadius: 6,
              textAlign: "center",
            }}
          >
            Cadastro realizado com sucesso.
            <br />
            Redirecionando...
          </div>
        )}

        <label>Nome de Usuário</label>

        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          style={inputStyle}
        />

        <label>E-mail</label>

        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          style={inputStyle}
        />

        <label>Senha</label>

        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          style={inputStyle}
        />

        <button
          type="submit"
          style={buttonStyle}
        >
          CADASTRAR NO DOJO
        </button>

        <p
          style={{
            textAlign: "center",
            marginTop: 20,
          }}
        >
          Já possui uma conta?{" "}
          <Link
            to="/login"
            style={{
              color: "#3ea6ff",
              textDecoration: "none",
            }}
          >
            Entrar
          </Link>
        </p>
      </form>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "12px",
  marginTop: 8,
  marginBottom: 18,
  background: "#1d1d1d",
  border: "1px solid #444",
  borderRadius: 6,
  color: "#fff",
  boxSizing: "border-box",
};

const buttonStyle: React.CSSProperties = {
  width: "100%",
  padding: "14px",
  border: "none",
  borderRadius: 6,
  background: "#0066cc",
  color: "#fff",
  fontWeight: "bold",
  fontSize: 16,
  cursor: "pointer",
};