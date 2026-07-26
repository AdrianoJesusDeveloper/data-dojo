import { useState } from "react";
import {
  useNavigate,
  createFileRoute,
  Link,
  redirect,
} from "@tanstack/react-router";

import { api } from "../lib/api";

import bgTech from "../assets/plano_de_fundo_tecnologico.png";
import logoOficial from "../assets/logooicial.png";

export const Route = createFileRoute("/login")({
  beforeLoad: () => {
    if (typeof window === "undefined") return;

    const token = localStorage.getItem("token");

    if (token) {
      throw redirect({ to: "/" });
    }
  },
  component: Login,
});

export default function Login() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [error, setError] = useState("");

  const handleLogin = async (
    e: React.FormEvent<HTMLFormElement>
  ) => {
    e.preventDefault();

    setError("");

    try {
      const response = await api.post("/api/auth/login/", {
        username: email,
        email: email,
        password: password,
      });

      localStorage.setItem("token", response.data.key);

      navigate({ to: "/" });
    } catch (err: any) {
      if (err.response?.data) {
        const data = err.response.data;

        const errorMessage =
          data.non_field_errors?.[0] ||
          data.detail ||
          "Usuário ou senha incorretos.";

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
        onSubmit={handleLogin}
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
          Área do Aluno
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

        <label>Usuário ou E-mail</label>

        <input
          type="text"
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
          ENTRAR NO DOJO
        </button>

        <p
          style={{
            textAlign: "center",
            marginTop: 20,
          }}
        >
          Novo por aqui?{" "}
          <Link
            to="/register"
            style={{
              color: "#3ea6ff",
              textDecoration: "none",
            }}
          >
            Crie uma conta
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