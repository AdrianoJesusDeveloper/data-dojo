import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  token: string | null;

  isAuthenticated: boolean;

  isStaff: boolean;

  isSuperuser: boolean;

  accessLoaded: boolean;

  login: (token: string) => void;

  setAdministrativeAccess: (isStaff: boolean, isSuperuser: boolean) => void;

  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,

      isAuthenticated: false,

      isStaff: false,

      isSuperuser: false,

      accessLoaded: false,

      login: (token) =>
        set({
          token,
          isAuthenticated: true,
          isStaff: false,
          isSuperuser: false,
          accessLoaded: false,
        }),

      setAdministrativeAccess: (isStaff, isSuperuser) =>
        set({ isStaff, isSuperuser, accessLoaded: true }),

      logout: () =>
        set({
          token: null,
          isAuthenticated: false,
          isStaff: false,
          isSuperuser: false,
          accessLoaded: false,
        }),
    }),
    {
      name: "ddj-auth",
    }
  )
);
