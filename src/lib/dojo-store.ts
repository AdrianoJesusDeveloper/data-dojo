import { useEffect, useState, useCallback, useSyncExternalStore } from "react";

export type BeltId = "white" | "yellow" | "green" | "black";

export interface Belt {
  id: BeltId;
  name: string;
  minXp: number;
  color: string;
  kanji: string;
  motto: string;
}

export const BELTS: Belt[] = [
  {
    id: "white",
    name: "Faixa Branca",
    minXp: 0,
    color: "#E5E5E5",
    kanji: "初",
    motto: "O início da jornada Kaizen.",
  },
  {
    id: "yellow",
    name: "Faixa Amarela",
    minXp: 500,
    color: "#F4D03F",
    kanji: "光",
    motto: "A primeira luz do entendimento.",
  },
  {
    id: "green",
    name: "Faixa Verde",
    minXp: 1500,
    color: "#2ECC71",
    kanji: "成",
    motto: "O crescimento constante do dado.",
  },
  {
    id: "black",
    name: "Faixa Preta",
    minXp: 3500,
    color: "#0A0A0A",
    kanji: "道",
    motto: "O Caminho. Maestria absoluta.",
  },
];

export interface ChallengeLog {
  id: string;
  title: string;
  xp: number;
  hours: number;
  date: string; // ISO
}

export interface DojoState {
  studentName: string;
  xp: number;
  hours: number;
  streak: number;
  history: ChallengeLog[];
}

const STORAGE_KEY = "dojo:state:v1";

const seed = (): DojoState => ({
  studentName: "Sensei Aprendiz",
  xp: 420,
  hours: 12,
  streak: 5,
  history: [
    { id: "h1", title: "SQL: JOINs Avançados", xp: 80, hours: 1.5, date: daysAgo(9) },
    { id: "h2", title: "Python: Pandas Pipeline", xp: 120, hours: 2.0, date: daysAgo(7) },
    { id: "h3", title: "Estatística Bayesiana", xp: 60, hours: 1.0, date: daysAgo(5) },
    { id: "h4", title: "Modelagem Dimensional", xp: 70, hours: 1.5, date: daysAgo(3) },
    { id: "h5", title: "dbt: Macros & Tests", xp: 90, hours: 2.0, date: daysAgo(1) },
  ],
});

function daysAgo(n: number) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString();
}

function load(): DojoState {
  if (typeof window === "undefined") return seed();
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return seed();
    return JSON.parse(raw) as DojoState;
  } catch {
    return seed();
  }
}

let state: DojoState = typeof window !== "undefined" ? load() : seed();
const listeners = new Set<() => void>();

function emit() {
  if (typeof window !== "undefined") {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }
  listeners.forEach((l) => l());
}

export function getCurrentBelt(xp: number): Belt {
  let current = BELTS[0];
  for (const b of BELTS) if (xp >= b.minXp) current = b;
  return current;
}
export function getNextBelt(xp: number): Belt | null {
  return BELTS.find((b) => b.minXp > xp) ?? null;
}
export function beltProgress(xp: number): number {
  const cur = getCurrentBelt(xp);
  const next = getNextBelt(xp);
  if (!next) return 100;
  return Math.min(100, ((xp - cur.minXp) / (next.minXp - cur.minXp)) * 100);
}

export function useDojo() {
  const snap = useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => state,
    () => state,
  );

  const submitChallenge = useCallback((title: string, xp: number, hours: number) => {
    const prevBelt = getCurrentBelt(state.xp).id;
    state = {
      ...state,
      xp: state.xp + xp,
      hours: +(state.hours + hours).toFixed(2),
      history: [
        ...state.history,
        { id: crypto.randomUUID(), title, xp, hours, date: new Date().toISOString() },
      ],
    };
    const newBelt = getCurrentBelt(state.xp).id;
    emit();
    return { promoted: prevBelt !== newBelt, newBelt: getCurrentBelt(state.xp) };
  }, []);

  const reset = useCallback(() => {
    state = seed();
    emit();
  }, []);

  const fastForward = useCallback((amount: number) => {
    const prevBelt = getCurrentBelt(state.xp).id;
    state = { ...state, xp: state.xp + amount };
    const newBelt = getCurrentBelt(state.xp).id;
    emit();
    return { promoted: prevBelt !== newBelt, newBelt: getCurrentBelt(state.xp) };
  }, []);

  return { state: snap, submitChallenge, reset, fastForward };
}

// Hydration helper for components that need stable initial server render
export function useHydrated() {
  const [h, setH] = useState(false);
  useEffect(() => setH(true), []);
  return h;
}
