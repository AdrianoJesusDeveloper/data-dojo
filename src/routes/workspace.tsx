import { createFileRoute } from "@tanstack/react-router";
import { DojoHeader } from "@/components/DojoHeader";
import { useDojo, useHydrated } from "@/lib/dojo-store";
import { celebratePromotion, celebrateXp } from "@/lib/celebrate";
import { useState } from "react";
import { toast, Toaster } from "sonner";

export const Route = createFileRoute("/workspace")({
  head: () => ({
    meta: [
      { title: "Workspace de Treinamento · Data Driven Dojô" },
      { name: "description", content: "Player de aula + IDE integrada. Compile e submeta seu desafio para ganhar XP." },
    ],
  }),
  component: Workspace,
});

const STARTER_CODE = `-- Desafio: Top 3 categorias por receita líquida
-- Faixa Amarela · 120 XP

SELECT
  c.category_name,
  SUM(o.quantity * o.unit_price * (1 - o.discount)) AS net_revenue
FROM orders o
JOIN products p ON p.id = o.product_id
JOIN categories c ON c.id = p.category_id
WHERE o.status = 'completed'
GROUP BY c.category_name
ORDER BY net_revenue DESC
LIMIT 3;
`;

export default function Workspace() {
  const { state, submitChallenge } = useDojo();
  const hydrated = useHydrated();
  const [code, setCode] = useState(STARTER_CODE);
  const [output, setOutput] = useState<string>("$ aguardando submissão...");
  const [running, setRunning] = useState(false);

  const compileAndSubmit = async () => {
    setRunning(true);
    setOutput("$ compilando ast...\n$ executando contra dojo-db (sandbox)...");
    await new Promise((r) => setTimeout(r, 900));
    const pass = code.toLowerCase().includes("select") && code.includes("FROM");
    if (!pass) {
      setOutput("✗ Falha: a query precisa de SELECT ... FROM ...\nKaizen: revise e tente de novo.");
      toast.error("Desafio reprovado. Sem XP desta vez.");
      setRunning(false);
      return;
    }
    const result = submitChallenge("Top 3 categorias por receita", 120, 1.5);
    setOutput(
      [
        "✓ Compilação OK",
        "✓ 3 linhas retornadas",
        "─────────────────────────────",
        "category_name        net_revenue",
        "Eletrônicos          R$ 184.230,55",
        "Casa & Cozinha       R$  92.110,00",
        "Esportes             R$  77.840,32",
        "─────────────────────────────",
        `+120 XP · +1.5h de código`,
      ].join("\n"),
    );
    if (result.promoted) {
      celebratePromotion(result.newBelt.color);
      toast.success(`🥋 PROMOVIDO! Você agora é ${result.newBelt.name}`, { duration: 5000 });
    } else {
      celebrateXp();
      toast.success("Desafio aprovado! +120 XP");
    }
    setRunning(false);
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Toaster position="top-right" theme="dark" richColors />
      <DojoHeader />

      <main className="flex-1 mx-auto max-w-[1600px] w-full px-4 py-6 grid lg:grid-cols-2 gap-4">
        {/* LEFT — Video + instructions */}
        <section className="rounded-xl border border-border bg-card overflow-hidden flex flex-col">
          <div className="aspect-video relative bg-black flex items-center justify-center bg-grid-dojo">
            <div className="absolute inset-0" style={{ background: "radial-gradient(circle at center, rgba(0,87,184,0.35), transparent 70%)" }} />
            <button className="relative z-10 h-20 w-20 rounded-full bg-destructive flex items-center justify-center text-3xl text-destructive-foreground shadow-[0_0_50px_rgba(230,57,70,0.6)] hover:scale-105 transition">
              ▶
            </button>
            <div className="absolute bottom-0 inset-x-0 p-4 flex items-center gap-3 bg-gradient-to-t from-black/80 to-transparent">
              <span className="text-[10px] uppercase tracking-widest text-kaizen font-semibold">Aula 04 · Faixa Amarela</span>
              <span className="text-xs text-muted-foreground ml-auto font-mono">18:42</span>
            </div>
          </div>
          <div className="p-6 overflow-y-auto">
            <div className="text-xs uppercase tracking-widest text-muted-foreground">Lição em andamento</div>
            <h1 className="font-display font-bold text-2xl mt-1">Agregações de receita com JOINs</h1>
            <p className="mt-3 text-sm text-muted-foreground leading-relaxed">
              Neste treino você irá compor uma query analítica usando <code className="text-kaizen">SUM</code>,
              <code className="text-kaizen"> GROUP BY</code> e múltiplos <code className="text-kaizen">JOIN</code> para
              calcular receita líquida por categoria. A disciplina está nos detalhes — não esqueça do desconto.
            </p>
            <div className="mt-5 rounded-lg border border-border bg-background p-4">
              <div className="font-display font-semibold text-sm mb-2">⛩ Missão</div>
              <ol className="text-sm space-y-1.5 list-decimal list-inside text-muted-foreground marker:text-kaizen">
                <li>Selecione apenas pedidos <code className="text-foreground">completed</code></li>
                <li>Calcule a receita líquida considerando o desconto</li>
                <li>Retorne o Top 3 ordenado de forma decrescente</li>
              </ol>
            </div>
            <div className="mt-5 flex items-center gap-4 text-xs">
              <Badge color="#FFA500">+120 XP</Badge>
              <Badge color="#0057B8">+1.5h código</Badge>
              <Badge color="#E63946">Dificuldade média</Badge>
            </div>
          </div>
        </section>

        {/* RIGHT — IDE */}
        <section className="rounded-xl border border-border bg-[#0A0A0A] flex flex-col overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border bg-black">
            <div className="flex gap-1.5">
              <span className="h-3 w-3 rounded-full bg-destructive" />
              <span className="h-3 w-3 rounded-full bg-kaizen" />
              <span className="h-3 w-3 rounded-full bg-[#2ECC71]" />
            </div>
            <span className="ml-3 text-xs font-mono text-muted-foreground">~/dojo/desafios/joins-agregacao.sql</span>
            {hydrated && (
              <span className="ml-auto text-xs font-mono text-kaizen">{state.xp} XP</span>
            )}
          </div>
          <div className="flex-1 grid grid-rows-[1fr_auto_220px] min-h-[520px]">
            <textarea
              spellCheck={false}
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="w-full h-full bg-[#0A0A0A] text-[#E5E5E5] font-mono text-sm p-4 resize-none outline-none leading-relaxed selection:bg-kaizen/30"
            />
            <div className="border-t border-border p-3 bg-black">
              <button
                onClick={compileAndSubmit}
                disabled={running}
                className="w-full inline-flex items-center justify-center gap-2 rounded-md bg-destructive px-6 py-3.5 font-display font-bold text-destructive-foreground uppercase tracking-[0.15em] text-sm shadow-[0_8px_30px_-8px_rgba(230,57,70,0.8)] hover:shadow-[0_12px_36px_-6px_rgba(230,57,70,0.95)] disabled:opacity-60 transition"
              >
                {running ? "⏳ executando..." : "⚔ Compilar e submeter desafio"}
              </button>
            </div>
            <pre className="bg-black border-t border-border p-4 font-mono text-xs text-[#9EE493] overflow-auto whitespace-pre-wrap">
{output}
            </pre>
          </div>
        </section>
      </main>
    </div>
  );
}

function Badge({ color, children }: { color: string; children: React.ReactNode }) {
  return (
    <span
      className="rounded-full px-2.5 py-1 font-semibold border"
      style={{ color, borderColor: `${color}55`, background: `${color}14` }}
    >
      {children}
    </span>
  );
}
