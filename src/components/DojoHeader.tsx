import { Link, useRouterState, useNavigate } from "@tanstack/react-router";
import { useDojo, getCurrentBelt, useHydrated } from "@/lib/dojo-store";
import { BeltProgress } from "./BeltBadge";
import logoDojo from "../assets/logo_transparente.png";

export function DojoHeader({ compact = false }: { compact?: boolean }) {
  const { state } = useDojo() as any;
  const hydrated = useHydrated();
  const path = useRouterState({ select: (s) => s.location.pathname });
  const belt = getCurrentBelt(state.xp);
  const navigate = useNavigate();
  const handleLogout = () => { if (typeof window !== "undefined") { localStorage.removeItem("token"); localStorage.removeItem("profile_preview"); } navigate({ to: "/login" }); };
  const navItem = (to: string, label: string) => <Link to={to} className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${path === to ? "bg-secondary text-kaizen" : "text-muted-foreground hover:text-foreground"}`}>{label}</Link>;

  let rawPic: string | null = null;
  if (hydrated && typeof window !== "undefined") {
    const sAny = state as any;
    rawPic = sAny?.profile_picture || sAny?.profilePicture || sAny?.avatar || sAny?.photo || localStorage.getItem("profile_preview") || localStorage.getItem("profile_picture") || localStorage.getItem("profilePicture");
  }
  let profilePic: string | null = null;
  if (rawPic && typeof rawPic === "string" && rawPic.trim() !== "") {
    profilePic = rawPic.startsWith("http") || rawPic.startsWith("blob:") || rawPic.startsWith("data:") ? rawPic : `https://data-dojo.onrender.com/api/media/${rawPic.replace(/^\/?(media\/)?/, "")}`;
  }

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/85 backdrop-blur supports-backdrop-filter:bg-background/70">
      <div className="mx-auto max-w-7xl px-4 py-3 flex items-center gap-4">
        <Link to="/" className="flex items-center gap-2.5 group"><div className="h-9 w-9 rounded-md bg-destructive flex items-center justify-center font-display font-black text-destructive-foreground text-lg shadow-[0_0_24px_rgba(230,57,70,0.45)]"><img src={logoDojo} width="36" height="100" alt="Logo" /></div><div className="leading-tight"><div className="font-display font-bold tracking-tight">Data Driven Dojô</div><div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Kaizen · 改善</div></div></Link>
        <nav className="ml-4 hidden md:flex items-center gap-1">
          {navItem("/", "Início")}{navItem("/dashboard", "Dashboard")}{navItem("/workspace", "Workspace")}{navItem("/ai", "AI")}{navItem("/ai-sales", "Sales")}{navItem("/community", "Comunidade")}{navItem("/portfolio", "Portfólio")}{navItem("/conheca-sensey", "Conheça o Sensey")}{navItem("/profile", "Meu Perfil")}
          <button onClick={handleLogout} className="px-3 py-1.5 rounded-md text-sm font-medium text-destructive hover:bg-destructive/10 transition-colors ml-2 cursor-pointer">Sair 🚪</button>
        </nav>
        <div className="ml-auto flex items-center gap-5">
          {hydrated && !compact && <div className="hidden lg:block w-64"><BeltProgress xp={state.xp} /></div>}
          {hydrated && <Link to="/profile" className="flex items-center gap-3 rounded-lg px-3 py-2 hover:bg-secondary transition"><div className="h-12 w-12 rounded-full overflow-hidden border-2 flex items-center justify-center font-bold text-sm bg-muted" style={{ borderColor: belt.color }}>{profilePic ? <img src={profilePic} alt="Perfil" className="h-full w-full object-cover" /> : <span>{state.studentName ? state.studentName.split(" ").map((n:string)=>n[0]).slice(0,2).join("").toUpperCase() : "DD"}</span>}</div><div className="hidden lg:block leading-tight"><div className="font-bold text-sm">{state.studentName}</div><div className="text-xs text-muted-foreground">🥋 {belt.name}</div><div className="text-xs text-kaizen">⭐ {state.xp} XP</div></div></Link>}
        </div>
      </div>
    </header>
  );
}
