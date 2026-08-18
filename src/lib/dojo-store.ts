import { create } from "zustand";
import { persist } from "zustand/middleware";

export const BELTS = [
  { id: "white", name: "Faixa Branca", minXp: 0, color: "#ffffff", kanji: "白帯" },
  { id: "yellow", name: "Faixa Amarela", minXp: 100, color: "#fbbf24", kanji: "黄帯" },
  { id: "green", name: "Faixa Verde", minXp: 300, color: "#34d399", kanji: "緑帯" },
  { id: "blue", name: "Faixa Azul", minXp: 600, color: "#60a5fa", kanji: "青帯" },
  { id: "brown", name: "Faixa Marrom", minXp: 1000, color: "#d97706", kanji: "茶帯" },
  { id: "black", name: "Faixa Preta", minXp: 1500, color: "#111827", kanji: "黒帯" },
] as const;

export type Belt = (typeof BELTS)[number];

export interface DojoState {
  state: {
    xp: number;
    hours: number;
    streak: number;
    studentName: string;
    history: Array<{ date: string; xp: number }>;
  };
  fastForward: () => void;
  reset: () => void;
  updateStudentName: (newName: string) => void;
  submitChallenge: (
    lessonTitle: string,
    xpEarned: number,
    hours: number,
  ) => { promoted: boolean; newBelt: Belt };
}

export function getCurrentBelt(xp: number): Belt {
  return (
    [...BELTS].reverse().find((belt) => xp >= belt.minXp) ?? BELTS[0]
  );
}

export function getNextBelt(xp: number): Belt {
  return BELTS.find((belt) => belt.minXp > xp) ?? BELTS[BELTS.length - 1];
}

export function beltProgress(xp: number) {
  const current = getCurrentBelt(xp);
  const next = getNextBelt(xp);

  if (current.id === next.id) return 100;

  const progress =
    ((xp - current.minXp) / (next.minXp - current.minXp)) * 100;

  return Math.min(Math.max(progress, 0), 100);
}

export function useHydrated() {
  return true;
}

export const useDojo = create<DojoState>()(
  persist(
    (set, get) => ({
      state: {
        xp: 0,
        hours: 0,
        streak: 0,
        studentName: "Aluno",
        history: [],
      },
      fastForward: () =>
        set((store) => ({
          state: { ...store.state, xp: store.state.xp + 50 },
        })),
      reset: () =>
        set((store) => ({
          state: {
            ...store.state,
            xp: 0,
            hours: 0,
            streak: 0,
            history: [],
          },
        })),
      updateStudentName: (newName) =>
        set((store) => ({
          state: { ...store.state, studentName: newName },
        })),
      submitChallenge: (lessonTitle, xpEarned, hours) => {
        const previousXp = get().state.xp;
        const previousBelt = getCurrentBelt(previousXp);
        const nextXp = previousXp + xpEarned;
        const newBelt = getCurrentBelt(nextXp);
        const promoted = previousBelt.id !== newBelt.id;

        set((store) => ({
          state: {
            ...store.state,
            xp: nextXp,
            hours: store.state.hours + hours,
            streak: store.state.streak + 1,
            history: [
              ...store.state.history,
              {
                date: new Date().toISOString(),
                xp: xpEarned,
              },
            ],
          },
        }));

        void lessonTitle;
        return { promoted, newBelt };
      },
    }),
    { name: "dojo-storage" },
  ),
);

export const updateStudentName = (newName: string) => {
  useDojo.getState().updateStudentName(newName);
};
