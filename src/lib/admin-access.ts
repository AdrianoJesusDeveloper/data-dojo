import { redirect } from "@tanstack/react-router";

import { api } from "./api";
import { useAuthStore } from "./auth-store";

interface AdministrativeProfile {
  is_staff: boolean;
  is_superuser: boolean;
}

export function isAdministrativeProfile(profile: AdministrativeProfile): boolean {
  return profile.is_staff === true || profile.is_superuser === true;
}

export async function resolveAdministrativeAccess(): Promise<boolean> {
  const state = useAuthStore.getState();
  if (!state.token || !state.isAuthenticated) return false;
  if (state.accessLoaded) return state.isStaff || state.isSuperuser;

  try {
    const { data } = await api.get<AdministrativeProfile>("/api/user/profile/");
    useAuthStore.getState().setAdministrativeAccess(data.is_staff, data.is_superuser);
    return isAdministrativeProfile(data);
  } catch {
    return false;
  }
}

export async function requireAdministrativeAccess(): Promise<void> {
  if (typeof window === "undefined") return;
  if (!(await resolveAdministrativeAccess())) {
    throw redirect({ to: "/workspace", replace: true });
  }
}
