import { create } from "zustand";
import { persist } from "zustand/middleware";

export type AgentRole = "user" | "assistant";

export interface AIMessage {
  role: AgentRole;
  content: string;
  timestamp?: string;
}

export interface AIConversation {
  conversationId: string | null;
  /** Token para sessões anônimas (não autenticadas). */
  conversationToken: string | null;
  mentor: string;
  messages: AIMessage[];
}

export interface AIState {
  /** Agente selecionado atualmente. */
  selectedMentor: string;
  /** Histórico de conversas por chave de agente. */
  conversations: Record<string, AIConversation>;
  /** Indica se uma resposta está sendo aguardada. */
  loading: boolean;

  setMentor: (mentor: string) => void;
  addMessage: (mentor: string, message: AIMessage) => void;
  setConversation: (
    mentor: string,
    conversationId: string | null,
    conversationToken?: string | null
  ) => void;
  clearConversation: (mentor: string) => void;
  clearAll: () => void;
  setLoading: (loading: boolean) => void;
}

const defaultConversation = (mentor: string): AIConversation => ({
  conversationId: null,
  conversationToken: null,
  mentor,
  messages: [],
});

export const useAIStore = create<AIState>()(
  persist(
    (set) => ({
      selectedMentor: "dojo_ai",
      conversations: {},
      loading: false,

      setMentor: (mentor) => set({ selectedMentor: mentor }),

      addMessage: (mentor, message) =>
        set((state) => {
          const existing = state.conversations[mentor] ?? defaultConversation(mentor);
          return {
            conversations: {
              ...state.conversations,
              [mentor]: {
                ...existing,
                messages: [
                  ...existing.messages,
                  { ...message, timestamp: message.timestamp ?? new Date().toISOString() },
                ],
              },
            },
          };
        }),

      setConversation: (mentor, conversationId, conversationToken = null) =>
        set((state) => {
          const existing = state.conversations[mentor] ?? defaultConversation(mentor);
          return {
            conversations: {
              ...state.conversations,
              [mentor]: {
                ...existing,
                conversationId,
                conversationToken,
              },
            },
          };
        }),

      clearConversation: (mentor) =>
        set((state) => ({
          conversations: {
            ...state.conversations,
            [mentor]: defaultConversation(mentor),
          },
        })),

      clearAll: () => set({ conversations: {}, selectedMentor: "dojo_ai" }),

      setLoading: (loading) => set({ loading }),
    }),
    {
      name: "ddj-ai",
      // Não persistir o estado de loading entre recargas.
      partialize: (state) => ({
        selectedMentor: state.selectedMentor,
        conversations: state.conversations,
      }),
    }
  )
);
