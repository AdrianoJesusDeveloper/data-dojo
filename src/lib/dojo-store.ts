import { create } from "zustand";
import { persist } from "zustand/middleware";

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
  submitChallenge: (xpEarned: number) => void;
}

export const BELTS = [
  { id: "white", name: "Faixa Branca", minXp: 0, color: "#ffffff", kanji: "白帯" },
  { id: "yellow", name: "Faixa Amarela", minXp: 100, color: "#fbbf24", kanji: "黄帯" },
  { id: "green", name: "Faixa Verde", minXp: 300, color: "#34d399", kanji: "緑帯" },
  { id: "blue", name: "Faixa Azul", minXp: 600, color: "#60a5fa", kanji: "青帯" },
  { id: "brown", name: "Faixa Marrom", minXp: 1000, color: "#d97706", kanji: "茶帯" },
  { id: "black", name: "Faixa Preta", minXp: 1500, color: "#111827", kanji: "黒帯" },
];

export function getCurrentBelt(xp: number) {
  const sorted = [...BELTS].sort((a, b) => b.minXp - a.minXp);
  return sorted.find((b) => xp >= b.minXp) || BELTS[0];
}

export function getNextBelt(xp: number) {
  return (
    BELTS.find((belt) => belt.minXp > xp) ||
    BELTS[BELTS.length - 1]
  );
}


export function beltProgress(xp: number) {
  const current = getCurrentBelt(xp);
  const next = getNextBelt(xp);

  if (current.id === next.id) {
    return 100;
  }

  const progress =
    ((xp - current.minXp) /
      (next.minXp - current.minXp)) *
    100;

  return Math.min(Math.max(progress, 0), 100);
}

export function useHydrated() {
  return true;
}

export const useDojo = create<DojoState>()(
  persist(
    (set): DojoState => ({
      state: {
        xp: 0,
        hours: 0,
        streak: 0,
        studentName: "Aluno",
        history: [],
      },
      fastForward: () =>
        set((store: DojoState) => ({
          state: { ...store.state, xp: store.state.xp + 50 },
        })),
      reset: () =>
        set((store: DojoState) => ({
          state: {
            ...store.state,
            xp: 0,
            hours: 0,
            streak: 0,
            history: [],
          },
        })),
      updateStudentName: (newName: string) =>
        set((store: DojoState) => ({
          state: { ...store.state, studentName: newName },
        })),
      submitChallenge: (xpEarned: number) =>
        set((store: DojoState) => ({
          state: {
            ...store.state,
            xp: store.state.xp + xpEarned,
            hours: store.state.hours + 1,
            streak: store.state.streak + 1,
            history: [
              ...store.state.history,
              {
                date: new Date().toISOString(),
                xp: xpEarned,
              },
            ],
          },
        })),
    }),
    {
      name: "dojo-storage",
    }
  )
);

export const updateStudentName = (newName: string) => {
  useDojo.getState().updateStudentName(newName);
};
