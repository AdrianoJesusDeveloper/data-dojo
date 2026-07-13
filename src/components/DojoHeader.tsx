import { Link, useRouterState, useNavigate } from "@tanstack/react-router";
import { useDojo, getCurrentBelt, useHydrated } from "@/lib/dojo-store";
import { BeltBadge, BeltProgress } from "./BeltBadge";
import logoDojo from "../assets/logo_transparente.png";

export function DojoHeader({ compact = false }: { compact?: boolean }) {
  const { state } = useDojo();
  const hydrated = useHydrated();
  const path = useRouterState({ select: (s) => s.location.pathname });
  const belt = getCurrentBelt(state.xp);
  const navigate = useNavigate();

  // Função para limpar a sessão e deslogar do Dojô
  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate({ to: "/login" });
  };

  const navItem = (to: string, label: string) => (
    <Link
      to={to}
      className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
        path === to ? "bg-secondary text-kaizen" : "text-muted-foreground hover:text-foreground"
      }`}
    >
      {label}
    </Link>
  );

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/85 backdrop-blur supports-backdrop-filter:bg-background/70">
      <div className="mx-auto max-w-7xl px-4 py-3 flex items-center gap-4">
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="h-9 w-9 rounded-md bg-destructive flex items-center justify-center font-display font-black text-destructive-foreground text-lg shadow-[0_0_24px_rgba(230,57,70,0.45)]">
            <img src={logoDojo} width="36" height="100" />
          </div>
          <div className="leading-tight">
            <div className="font-display font-bold tracking-tight">Data Driven Dojô</div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
              Kaizen · 改善
            </div>
          </div>
        </Link>

        <nav className="ml-4 hidden md:flex items-center gap-1">
          {navItem("/", "Início")}
          {navItem("/dashboard", "Dashboard")}
          {navItem("/workspace", "Workspace")}
          {navItem("/community", "Comunidade")}

          {/* Botão de Logout integrado na navegação estilizado de forma discreta */}
          <button
            onClick={handleLogout}
            className="px-3 py-1.5 rounded-md text-sm font-medium text-destructive hover:bg-destructive/10 transition-colors ml-2 cursor-pointer"
          >
            Sair 🚪
          </button>
        </nav>

        <div className="ml-auto flex items-center gap-5">
          {hydrated && !compact && (
            <div className="hidden lg:block w-64">
              <BeltProgress xp={state.xp} />
            </div>
          )}
          {hydrated && (
            <Link 
              to="/profile" 
              className="transition-transform hover:scale-105 active:scale-95 focus:outline-none"
              title="Ver meu perfil Kaizen"
            >
              <BeltBadge belt={belt} size={compact ? "sm" : "md"} />
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}