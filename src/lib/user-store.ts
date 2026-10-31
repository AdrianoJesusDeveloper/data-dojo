import { create } from "zustand";
import { persist } from "zustand/middleware";
import { api } from "./api";

export interface UserProfile {
  id: number | null;
  username: string;
  email: string;
  firstName: string;
  lastName: string;
  /** URL relativa ou absoluta da foto de perfil. */
  profilePicture: string | null;
  bio: string;
  /** Data de ingresso no Dojô (ISO 8601). */
  dateJoined: string | null;
}

interface UserState {
  profile: UserProfile | null;
  /** true enquanto o perfil está sendo buscado da API. */
  loading: boolean;
  /** Mensagem de erro da última busca, ou null se ok. */
  error: string | null;

  setProfile: (profile: UserProfile) => void;
  updateProfile: (partial: Partial<UserProfile>) => void;
  clearProfile: () => void;
  fetchProfile: () => Promise<void>;
}

const emptyProfile: UserProfile = {
  id: null,
  username: "",
  email: "",
  firstName: "",
  lastName: "",
  profilePicture: null,
  bio: "",
  dateJoined: null,
};

export const useUserStore = create<UserState>()(
  persist(
    (set, get) => ({
      profile: null,
      loading: false,
      error: null,

      setProfile: (profile) => set({ profile, error: null }),

      updateProfile: (partial) => {
        const current = get().profile ?? emptyProfile;
        set({ profile: { ...current, ...partial } });
      },

      clearProfile: () => set({ profile: null, error: null }),

      fetchProfile: async () => {
        set({ loading: true, error: null });
        try {
          const { data } = await api.get<{
            id: number;
            username: string;
            email: string;
            first_name: string;
            last_name: string;
            profile_picture: string | null;
            bio: string;
            date_joined: string;
          }>("/api/profile/");

          set({
            profile: {
              id: data.id,
              username: data.username,
              email: data.email,
              firstName: data.first_name,
              lastName: data.last_name,
              profilePicture: data.profile_picture ?? null,
              bio: data.bio ?? "",
              dateJoined: data.date_joined ?? null,
            },
            loading: false,
          });
        } catch (err: unknown) {
          const message =
            err instanceof Error ? err.message : "Não foi possível carregar o perfil.";
          set({ loading: false, error: message });
        }
      },
    }),
    {
      name: "ddj-user",
      partialize: (state) => ({ profile: state.profile }),
    }
  )
);
