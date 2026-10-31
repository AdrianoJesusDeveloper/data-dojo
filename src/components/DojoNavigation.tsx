/**
 * DojoNavigation
 *
 * Navegação lateral/móvel compacta para uso dentro de páginas que precisam
 * de um menu secundário (ex.: Workspace, Library, Studio). É diferente do
 * DojoHeader (navbar global): este componente traz links contextuais da seção.
 */
import { Link, useRouterState } from "@tanstack/react-router";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  BookOpen,
  Bot,
  Briefcase,
  ShoppingBag,
  User,
  Monitor,
  Home,
} from "lucide-react";
import { useAuthStore } from "@/lib/auth-store";

interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
  adminOnly?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Início", icon: <Home size={18} /> },
  { to: "/dashboard", label: "Dashboard", icon: <LayoutDashboard size={18} /> },
  { to: "/workspace", label: "Workspace", icon: <Monitor size={18} /> },
  { to: "/library", label: "Biblioteca", icon: <BookOpen size={18} /> },
  { to: "/ai", label: "DDJ AI", icon: <Bot size={18} /> },
  { to: "/professional-studio", label: "Project Studio", icon: <Briefcase size={18} />, adminOnly: true },
  { to: "/store", label: "3DStore", icon: <ShoppingBag size={18} /> },
  { to: "/profile", label: "Meu Perfil", icon: <User size={18} /> },
];

interface DojoNavigationProps {
  /** Orientação do menu. Padrão: "vertical". */
  orientation?: "vertical" | "horizontal";
  className?: string;
}

export function DojoNavigation({
  orientation = "vertical",
  className,
}: DojoNavigationProps) {
  const path = useRouterState({ select: (s) => s.location.pathname });
  const isAdmin = useAuthStore((auth) => auth.isStaff || auth.isSuperuser);

  const visibleItems = NAV_ITEMS.filter((item) => !item.adminOnly || isAdmin);

  const isActive = (to: string) => {
    if (to === "/") return path === "/";
    return path.startsWith(to);
  };

  return (
    <nav
      aria-label="Navegação do Dojô"
      className={cn(
        orientation === "vertical"
          ? "flex flex-col gap-1"
          : "flex flex-row flex-wrap gap-1",
        className
      )}
    >
      {visibleItems.map((item) => (
        <Link
          key={item.to}
          to={item.to}
          className={cn(
            "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
            isActive(item.to)
              ? "bg-secondary text-kaizen"
              : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"
          )}
          aria-current={isActive(item.to) ? "page" : undefined}
        >
          <span className="shrink-0">{item.icon}</span>
          <span>{item.label}</span>
        </Link>
      ))}
    </nav>
  );
}
