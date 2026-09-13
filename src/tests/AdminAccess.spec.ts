import { beforeEach, describe, expect, it, vi } from "vitest";

const { get } = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("@/lib/api", () => ({ api: { get } }));

import {
  requireAdministrativeAccess,
  resolveAdministrativeAccess,
} from "../lib/admin-access";
import { useAuthStore } from "../lib/auth-store";
import { Route as ProjectStudioRoute } from "../routes/professional-studio";
import { Route as ContentStudioRoute } from "../routes/content-studio";

describe("shared administrative route guard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      token: "token",
      isAuthenticated: true,
      isStaff: false,
      isSuperuser: false,
      accessLoaded: true,
    });
  });

  it("is installed on Project Studio and Content Studio routes", () => {
    expect(ProjectStudioRoute.options.beforeLoad).toBe(requireAdministrativeAccess);
    expect(ContentStudioRoute.options.beforeLoad).toBe(requireAdministrativeAccess);
  });

  it("redirects a student who types either protected URL", async () => {
    await expect(requireAdministrativeAccess()).rejects.toBeTruthy();
  });

  it("allows staff and superusers", async () => {
    useAuthStore.setState({ isStaff: true, isSuperuser: false, accessLoaded: true });
    await expect(requireAdministrativeAccess()).resolves.toBeUndefined();

    useAuthStore.setState({ isStaff: false, isSuperuser: true, accessLoaded: true });
    await expect(requireAdministrativeAccess()).resolves.toBeUndefined();
  });

  it("loads trusted flags from the authenticated profile", async () => {
    useAuthStore.setState({ accessLoaded: false });
    get.mockResolvedValue({ data: { is_staff: false, is_superuser: true } });
    await expect(resolveAdministrativeAccess()).resolves.toBe(true);
    expect(useAuthStore.getState().isSuperuser).toBe(true);
  });
});
