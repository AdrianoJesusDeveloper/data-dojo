import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  HeadContent,
  Scripts,
  redirect,
} from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";

import appCss from "../styles.css?url";
import { reportLovableError } from "../lib/lovable-error-reporting";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <p className="font-mono text-sm font-medium text-kaizen">DOJÔ / 404</p>
        <h1 className="mt-2 text-7xl font-bold text-foreground">404</h1>
        <h2 className="mt-4 text-xl font-semibold text-foreground">Página não encontrada</h2>
        <p className="mt-2 text-sm text-muted-foreground">O caminho informado não existe ou foi movido.</p>
        <Link to="/" className="mt-6 inline-flex min-h-11 items-center justify-center rounded-md bg-primary px-5 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90">Voltar ao Dojô</Link>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  console.error(error);
  const router = useRouter();
  useEffect(() => { reportLovableError(error, { boundary: "tanstack_root_error_component" }); }, [error]);
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <p className="font-mono text-sm font-medium text-samurai">DOJÔ / ERRO</p>
        <h1 className="mt-2 text-xl font-semibold tracking-tight text-foreground">Não foi possível carregar esta página</h1>
        <p className="mt-2 text-sm text-muted-foreground">O Dojô encontrou um problema. Tente novamente ou volte para a página inicial.</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <button onClick={() => { router.invalidate(); reset(); }} className="inline-flex min-h-11 items-center justify-center rounded-md bg-primary px-5 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90">Tentar novamente</button>
          <Link to="/" className="inline-flex min-h-11 items-center justify-center rounded-md border border-input bg-background px-5 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground">Ir para o início</Link>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  beforeLoad: ({ location }) => {
    if (typeof window === "undefined") return;
    const publicRoutes = ["/", "/login", "/register", "/portfolio", "/store"];
    if (publicRoutes.includes(location.pathname)) return;
    const authStorage = window.localStorage.getItem("ddj-auth");
    let isAuthenticated = false;
    if (authStorage) {
      try {
        const parsed = JSON.parse(authStorage);
        isAuthenticated = parsed?.state?.isAuthenticated === true && !!parsed?.state?.token;
      } catch { isAuthenticated = false; }
    }
    if (!isAuthenticated) throw redirect({ to: "/login" });
  },
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1, viewport-fit=cover" },
      { title: "Data Driven Dojô — Treinamento Kaizen para profissionais de dados" },
      { name: "description", content: "Data Driven Dojô: uma jornada gamificada de aprendizagem em dados, engenharia, IA e tecnologia, baseada em prática, disciplina e Kaizen." },
      { name: "theme-color", content: "#1C1C1C" },
      { name: "color-scheme", content: "dark" },
      { name: "application-name", content: "Data Driven Dojô" },
      { property: "og:title", content: "Data Driven Dojô" },
      { property: "og:description", content: "Disciplina samurai aplicada ao aprendizado de dados e tecnologia." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
    links: [
      { rel: "stylesheet", href: appCss },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      { rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "anonymous" },
      { rel: "stylesheet", href: "https://fonts.googleapis.com/css2?family=Exo+2:wght@500;600;700;800&family=Open+Sans:wght@400;500;600&family=Roboto+Mono:wght@400;500;700&display=swap" },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: ReactNode }) {
  return <html lang="pt-BR"><head><HeadContent /></head><body>{children}<Scripts /></body></html>;
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();
  return <QueryClientProvider client={queryClient}><Outlet /></QueryClientProvider>;
}
