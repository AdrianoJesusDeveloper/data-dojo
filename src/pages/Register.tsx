import { useState } from "react";

import {
  useNavigate,
  Link,
} from "@tanstack/react-router";

import { api } from "../lib/api";

import bgTech from "../assets/plano_de_fundo_tecnologico.png";
import logoOficial from "../assets/logooicial.png";


export default function Register() {
  component: Register
};


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