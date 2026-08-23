import { useState } from "react";
import { Link, useNavigate, useSearch } from "@tanstack/react-router";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import bgTech from "@/assets/plano_de_fundo_tecnologico.png";
import logoOficial from "@/assets/logooicial.png";

interface LoginSearch { redirect?: string; }

export default function Login() {
  const navigate = useNavigate();
  const search = useSearch({ from: "/login" }) as LoginSearch;
  const redirect = search.redirect ?? "/workspace";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleLogin(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await api.post("/api/auth/login/", { username: email, email, password });
      const token = response.data.key;
      if (!token) throw new Error("Servidor não retornou um token.");
      useAuthStore.getState().login(token);
      navigate({ to: redirect, replace: true });
    } catch (err: any) {
      const data = err?.response?.data;
      setError(data?.non_field_errors?.[0] ?? data?.detail ?? "Usuário ou senha incorretos.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display:"flex", justifyContent:"center", alignItems:"center", width:"100vw", height:"100vh", position:"relative", color:"#fff", fontFamily:"sans-serif", backgroundImage:`linear-gradient(rgba(0,0,0,.65), rgba(0,0,0,.65)), url(${bgTech})`, backgroundSize:"cover", backgroundPosition:"center", backgroundRepeat:"no-repeat" }}>
      <div style={{ position:"absolute", top:24, left:24 }}><img src={logoOficial} alt="Data Driven Dojo" style={{ height:60, borderRadius:8, boxShadow:"0 4px 12px rgba(0,0,0,.35)" }} /></div>
      <form onSubmit={handleLogin} style={{ width:380, padding:40, borderRadius:12, background:"rgba(17,17,17,.88)", backdropFilter:"blur(8px)", border:"1px solid rgba(255,255,255,.08)", boxShadow:"0 8px 30px rgba(0,0,0,.6)" }}>
        <h2 style={{ textAlign:"center", marginBottom:30, letterSpacing:2 }}>Área do Aluno</h2>
        {error && <div style={{ background:"#3b1111", color:"#ff8080", padding:12, borderRadius:6, marginBottom:20, textAlign:"center" }}>{error}</div>}
        <label>Usuário ou E-mail</label>
        <input type="text" value={email} required onChange={(e) => setEmail(e.target.value)} style={inputStyle} />
        <label>Senha</label>
        <input type="password" value={password} required onChange={(e) => setPassword(e.target.value)} style={inputStyle} />
        <div style={{ textAlign:"right", marginTop:-8, marginBottom:18 }}><Link to="/recuperar-senha" style={{ color:"#ff8a65", textDecoration:"none", fontSize:13 }}>Esqueci minha senha</Link></div>
        <button type="submit" disabled={loading} style={{ ...buttonStyle, opacity: loading ? .7 : 1 }}>{loading ? "Entrando..." : "ENTRAR NO DOJO"}</button>
        <p style={{ marginTop:20, textAlign:"center" }}>Novo por aqui? <Link to="/register" style={{ color:"#3ea6ff", textDecoration:"none" }}>Crie uma conta</Link></p>
      </form>
    </div>
  );
}

const inputStyle: React.CSSProperties = { width:"100%", padding:"12px", marginTop:8, marginBottom:18, background:"#1d1d1d", border:"1px solid #444", borderRadius:6, color:"#fff", boxSizing:"border-box" };
const buttonStyle: React.CSSProperties = { width:"100%", padding:"14px", border:"none", borderRadius:6, background:"#0066cc", color:"#fff", fontWeight:"bold", fontSize:16, cursor:"pointer" };
