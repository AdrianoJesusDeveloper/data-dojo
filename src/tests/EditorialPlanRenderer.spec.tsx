import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";

import { EditorialPlanRenderer, SafeCodeBlock } from "@/components/content-studio/EditorialPlanRenderer";

const challenge = {
  independent_explanation: "Explique com suas próprias palavras",
  practical_challenge: "Construa sem delegar a decisão",
  portfolio_artifact: "Notebook reproduzível",
  responsible_ai_use: "Registre onde a IA ajudou",
};

describe("EditorialPlanRenderer", () => {
  it("renders premium modules, lessons, AI policy, authorship and compact sources", () => {
    render(<EditorialPlanRenderer projectType="premium" citations={[{ id: 1, book_title: "Livro do Dojô", page_number: 42, excerpt: "Um trecho curto e verificável." }]} plan={{
      title: "Formação em Dados", general_objective: "Formar profissionais", professional_objective: "Entregar projetos", target_audience: "Analistas", level: "Intermediário", total_workload: "40h", technology_stack: ["Python", "SQL"],
      modules: [{ title: "Fundamentos", objective: "Compreender dados", lessons: [{ title: "Primeira análise", objective: "Investigar", concepts: ["hipótese"], practice: "Analisar antes de pedir ajuda", ai_integration: "Sugerir casos de borda", validation: "Executar testes", authorship_challenge: challenge }], exercises: ["Exercício 1"], kata: "Kata SQL", practical_project: "Painel", assessment: "Rubrica" }],
      final_project: "Produto de dados", certification_requirements: "Aprovação humana", sources: [],
    }} />);

    expect(screen.getByText("Formação em Dados")).toBeInTheDocument();
    expect(screen.getByText(/Módulo 1/)).toBeInTheDocument();
    expect(screen.getByText("Primeira análise")).toBeInTheDocument();
    expect(screen.getByText("O ALUNO FAZ")).toBeInTheDocument();
    expect(screen.getByText("A IA PODE AUXILIAR")).toBeInTheDocument();
    expect(screen.getByText("O ALUNO DEVE VALIDAR")).toBeInTheDocument();
    expect(screen.getByText("Desafio sem IA")).toBeInTheDocument();
    expect(screen.getByText(/Compreender → Raciocinar → Estruturar/)).toBeInTheDocument();
    expect(screen.getByText("Desafio de Autoria")).toBeInTheDocument();
    expect(screen.getByText("Livro do Dojô · p. 42")).toBeInTheDocument();
  });

  it("renders YouTube as one theme, lesson and video", () => {
    render(<EditorialPlanRenderer projectType="youtube" plan={{ title: "Playlist responsável", objective: "Ensinar", target_audience: "Iniciantes", level: "Básico", video_count: 1, tools: ["Python"], videos: [{ theme: "Tema único", title: "Vídeo único", objective: "Praticar", practical_demo: "Demo", exercise: "Refaça", human_reasoning: "Defina a hipótese", ai_integration: "Revise alternativas", validation: "Confira a saída", authorship_challenge: challenge }] }} />);
    expect(screen.getByText("1 tema = 1 aula = 1 vídeo")).toBeInTheDocument();
    expect(screen.getByText("Vídeo único")).toBeInTheDocument();
    expect(screen.getByText("Desafio de Autoria")).toBeInTheDocument();
  });

  it("renders code as text and copies the original code safely", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    const code = '<script>alert("não executar")</script>';
    const { container } = render(<SafeCodeBlock language="html" code={code} />);
    expect(container.querySelector("pre code")).toHaveTextContent(code);
    expect(container.querySelector("script")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Copiar" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(code));
  });

  it("shows planned illustrations without generating or injecting markup", () => {
    render(<EditorialPlanRenderer projectType="youtube" plan={{ title: "Visual", videos: [{ title: "Aula", human_reasoning: "Pensar", ai_integration: "Apoiar", validation: "Validar", authorship_challenge: challenge, concepts: [{ type: "illustration", description: "Fluxo desenhado do pipeline" }] }] }} />);
    expect(screen.getByText("Ilustração planejada")).toBeInTheDocument();
    expect(screen.getByText("Fluxo desenhado do pipeline")).toBeInTheDocument();
  });

  it("marks persisted old plans as legacy instead of presenting them as editorial v1", () => {
    render(<EditorialPlanRenderer projectType="premium" plan={{ source_summary: "Resumo antigo", proposed_architecture: { components: ["API"] }, risks: ["Legado"] }} />);
    expect(screen.getByText("Plano legado")).toBeInTheDocument();
    expect(screen.getByText(/anterior ao contrato editorial v1/)).toBeInTheDocument();
    expect(screen.queryByText("Formação Premium")).not.toBeInTheDocument();
  });
});
