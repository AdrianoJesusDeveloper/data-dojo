import { createFileRoute } from "@tanstack/react-router";
import { DojoHeader } from "@/components/DojoHeader";
import { BeltBadge, BeltProgress } from "@/components/BeltBadge";
import { celebratePromotion, celebrateXp } from "@/lib/celebrate";
import { toast, Toaster } from "sonner";
import { useDojo, getCurrentBelt, BELTS, useHydrated } from "@/lib/dojo-store";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useMemo } from "react";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Dashboard do Aluno · Data Driven Dojô" },
      { name: "description", content: "Acompanhe seu XP, horas treinadas, evolução de faixas e progresso Kaizen." },
    ],
  }),
  component: Dashboard,
});

function Dashboard() {
  const { state, fastForward, reset } = useDojo();
  const hydrated = useHydrated();
  const belt = getCurrentBelt(state.xp);

  const chartData = useMemo(() => {
    const sorted = [...state.history].sort((a, b) => a.date.localeCompare(b.date));
    let cum = 0;
    return sorted.map((h) => {
      cum += h.xp;
      return {
        date: new Date(h.date).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" }),
        xp: h.xp,
        hours: h.hours,
        cumulative: cum,
      };
    });
  }, [state.history]);

  // Frequência Kaizen — XP por dia nos últimos 7 dias
  const weeklyData = useMemo(() => {
    const days: { label: string; key: string; xp: number }[] = [];
    const fmt = new Intl.DateTimeFormat("pt-BR", { weekday: "short" });
    for (let i = 6; i >= 0; i--) {
      const d = new Date();
      d.setHours(0, 0, 0, 0);
      d.setDate(d.getDate() - i);
      days.push({
        key: d.toISOString().slice(0, 10),
        label: fmt.format(d).replace(".", ""),
        xp: 0,
      });
    }
    for (const h of state.history) {
      const k = h.date.slice(0, 10);
      const day = days.find((d) => d.key === k);
      if (day) day.xp += h.xp;
    }
    return days;
  }, [state.history]);

  // Domínio de Habilidades (derivado do XP total — escala 0..100)
  const skillsData = useMemo(() => {
    const cap = (n: number) => Math.min(100, Math.round(n));
    const base = state.xp;
    return [
      { skill: "SQL", nivel: cap(base / 18 + 10) },
      { skill: "Python", nivel: cap(base / 22 + 5) },
      { skill: "Dataviz", nivel: cap(base / 28) },
      { skill: "Modelagem", nivel: cap(base / 32) },
    ];
  }, [state.xp]);


  if (!hydrated) {
    return (
      <div className="min-h-screen">
        <DojoHeader />
        <div className="mx-auto max-w-7xl px-4 py-10 text-muted-foreground">Carregando dashboard…</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Toaster position="top-right" theme="dark" richColors />
      <DojoHeader />
      <main className="mx-auto max-w-7xl px-4 py-10">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <div className="text-xs uppercase tracking-[0.25em] text-muted-foreground">Dashboard do Aluno</div>
            <h1 className="font-display font-extrabold text-4xl mt-1">Olá, {state.studentName}</h1>
            <p className="text-muted-foreground mt-1">Seu caminho Kaizen em números.</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => {
                const r = fastForward(250);
                if (r.promoted) {
                  celebratePromotion(r.newBelt.color);
                  toast.success(`🥋 PROMOVIDO! Você agora é ${r.newBelt.name}`, { duration: 5000 });
                } else {
                  celebrateXp();
                  toast.success("+250 XP Kaizen!");
                }
              }}
              className="rounded-md border border-kaizen/40 bg-kaizen/10 text-kaizen px-4 py-2 text-sm font-semibold hover:bg-kaizen/20"
            >
              + 250 XP (demo)
            </button>
            <button
              onClick={reset}
              className="rounded-md border border-border bg-secondary px-4 py-2 text-sm font-semibold text-muted-foreground hover:text-foreground"
            >
              Resetar progresso
            </button>
          </div>
        </div>

        {/* KPI row */}
        <div className="mt-8 grid md:grid-cols-4 gap-4">
          <KpiCard label="Pontos Kaizen" value={`${state.xp} XP`} accent="#FFA500" />
          <KpiCard label="Horas de Código" value={`${state.hours.toFixed(1)}h`} accent="#0057B8" />
          <KpiCard label="Sequência" value={`${state.streak} dias`} accent="#E63946" />
          <div className="rounded-xl border border-border bg-card p-5">
            <div className="text-xs uppercase tracking-widest text-muted-foreground">Faixa Atual</div>
            <div className="mt-3"><BeltBadge belt={belt} /></div>
          </div>
        </div>

        {/* Progress to next */}
        <div className="mt-6 rounded-xl border border-border bg-card p-6">
          <div className="flex items-baseline justify-between mb-4">
            <h2 className="font-display font-bold text-xl">Progresso de Graduação</h2>
            <span className="text-xs text-muted-foreground italic">"{belt.motto}"</span>
          </div>
          <BeltProgress xp={state.xp} />
        </div>

        {/* Charts */}
        <div className="mt-6 grid lg:grid-cols-2 gap-4">
          <ChartCard title="XP Acumulado (Trilha Kaizen)">
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={chartData} margin={{ top: 10, right: 12, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="xpGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#FFA500" stopOpacity={0.7} />
                    <stop offset="100%" stopColor="#FFA500" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#2F2F2F" strokeDasharray="3 3" />
                <XAxis dataKey="date" stroke="#9CA3AF" fontSize={11} />
                <YAxis stroke="#9CA3AF" fontSize={11} />
                <Tooltip
                  contentStyle={{ background: "#1C1C1C", border: "1px solid #2F2F2F", borderRadius: 8 }}
                  labelStyle={{ color: "#E5E5E5" }}
                />
                <Area type="monotone" dataKey="cumulative" stroke="#FFA500" strokeWidth={2.5} fill="url(#xpGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Horas Treinadas por Desafio">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={chartData} margin={{ top: 10, right: 12, left: -10, bottom: 0 }}>
                <CartesianGrid stroke="#2F2F2F" strokeDasharray="3 3" />
                <XAxis dataKey="date" stroke="#9CA3AF" fontSize={11} />
                <YAxis stroke="#9CA3AF" fontSize={11} />
                <Tooltip
                  contentStyle={{ background: "#1C1C1C", border: "1px solid #2F2F2F", borderRadius: 8 }}
                />
                <Bar dataKey="hours" fill="#FFA500" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>

        {/* Belts collection */}
        <div className="mt-6 rounded-xl border border-border bg-card p-6">
          <h2 className="font-display font-bold text-xl mb-4">Badges Conquistados</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {BELTS.map((b) => {
              const earned = state.xp >= b.minXp;
              return (
                <div
                  key={b.id}
                  className={`rounded-lg border p-4 transition ${
                    earned ? "border-kaizen/50 bg-background" : "border-border bg-background/40 opacity-50"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className="h-12 w-12 rounded-md flex items-center justify-center font-display font-bold border-2 border-black/40"
                      style={{ background: b.color, color: b.id === "black" ? "#FFA500" : "#1C1C1C" }}
                    >
                      {b.kanji}
                    </div>
                    <div>
                      <div className="font-display font-semibold text-sm">{b.name}</div>
                      <div className="text-[11px] font-mono text-muted-foreground">{b.minXp} XP</div>
                    </div>
                  </div>
                  <div className="mt-2 text-[11px] text-muted-foreground">
                    {earned ? "✓ Conquistado" : "Bloqueado"}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* History */}
        <div className="mt-6 rounded-xl border border-border bg-card p-6">
          <h2 className="font-display font-bold text-xl mb-4">Histórico de Desafios</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wider text-muted-foreground border-b border-border">
                <tr><th className="py-2">Data</th><th>Desafio</th><th className="text-right">Horas</th><th className="text-right">XP</th></tr>
              </thead>
              <tbody>
                {[...state.history].reverse().map((h) => (
                  <tr key={h.id} className="border-b border-border/60">
                    <td className="py-2.5 font-mono text-xs text-muted-foreground">
                      {new Date(h.date).toLocaleDateString("pt-BR")}
                    </td>
                    <td>{h.title}</td>
                    <td className="text-right font-mono">{h.hours.toFixed(1)}</td>
                    <td className="text-right font-mono text-kaizen">+{h.xp}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}

function KpiCard({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div className="relative rounded-xl border border-border bg-card p-5 overflow-hidden">
      <div className="absolute top-0 left-0 h-1 w-full" style={{ background: accent }} />
      <div className="text-xs uppercase tracking-widest text-muted-foreground">{label}</div>
      <div className="mt-2 font-display font-extrabold text-3xl" style={{ color: accent }}>{value}</div>
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <h2 className="font-display font-bold text-xl mb-3">{title}</h2>
      {children}
    </div>
  );
}
