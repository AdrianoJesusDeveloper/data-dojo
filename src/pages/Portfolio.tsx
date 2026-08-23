import { useEffect, useMemo, useState } from "react";
import { DojoHeader } from "@/components/DojoHeader";
import { api } from "@/lib/api";

interface Profile {
  username: string;
  email: string;
  profile_picture: string | null;
  xp_points: number;
}

interface GithubRepo {
  id: number;
  name: string;
  html_url: string;
  description: string | null;
  language: string | null;
  topics?: string[];
  stargazers_count: number;
  fork: boolean;
}

const destaques = [
  {
    nome: "Data Driven Dojô",
    tipo: "PROJETO PRINCIPAL",
    descricao:
      "Plataforma educacional criada para unir aprendizagem, dados, IA, comunidade e evolução Kaizen em uma única experiência.",
    tecnologias: ["React", "TypeScript", "Django", "Python", "PostgreSQL", "IA"],
    github: "https://github.com/AdrianoJesusDeveloper/data-dojo",
  },
  {
    nome: "Dashboard de DRE — SG Global Group",
    tipo: "DATA ANALYTICS",
    descricao:
      "Dashboard orientado à análise da Demonstração do Resultado do Exercício para apoiar decisões gerenciais.",
    tecnologias: ["Python", "SQL", "Power BI", "Data Analytics"],
    github: "https://github.com/AdrianoJesusDeveloper/Dashboard_de_DRE_SG-Global_Group_DNC",
  },
];

export default function PortfolioPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [repos, setRepos] = useState<GithubRepo[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(true);

  useEffect(() => {
    api.get<Profile>("/api/user/profile/").then(({ data }) => setProfile(data)).catch(() => undefined);

    fetch(
      "https://api.github.com/users/AdrianoJesusDeveloper/repos?per_page=30&sort=updated"
    )
      .then((response) => response.ok ? response.json() : [])
      .then((data: GithubRepo[]) => setRepos(data.filter((repo) => !repo.fork)))
      .catch(() => setRepos([]))
      .finally(() => setLoadingRepos(false));
  }, []);

  const githubProjects = useMemo(() => repos.slice(0, 8), [repos]);

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <DojoHeader />

      <section className="mx-auto max-w-7xl px-8 py-16">
        <div className="flex flex-col gap-8 md:flex-row md:items-center md:justify-between">
          <div>
            <span className="font-semibold tracking-widest text-orange-500">DATA DRIVEN DOJO</span>
            <h1 className="mt-4 text-5xl font-black">Portfólio de Projetos</h1>
            <p className="mt-5 max-w-3xl text-lg text-zinc-400">
              Engenharia de Dados, Business Intelligence, Ciência de Dados, IA, Cloud e desenvolvimento Full Stack.
            </p>
          </div>
          {profile?.profile_picture && (
            <div className="flex items-center gap-4">
              <img src={profile.profile_picture} alt={profile.username} className="h-24 w-24 rounded-full object-cover border-2 border-orange-500" />
              <div>
                <p className="text-xl font-bold">{profile.username}</p>
                <p className="text-zinc-400">{profile.xp_points} XP Kaizen</p>
              </div>
            </div>
          )}
        </div>

        <div className="mt-10 flex flex-wrap gap-4">
          <a href="https://www.linkedin.com/in/adriano-jesus-costa/" target="_blank" rel="noreferrer" className="rounded-xl bg-orange-500 px-6 py-3 font-bold hover:bg-orange-600">LinkedIn</a>
          <a href="https://github.com/AdrianoJesusDeveloper" target="_blank" rel="noreferrer" className="rounded-xl border border-zinc-700 px-6 py-3 font-bold hover:border-orange-500">GitHub</a>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-8 pb-20">
        <h2 className="mb-10 text-3xl font-bold">Projetos em Destaque</h2>
        <div className="grid gap-8 lg:grid-cols-2">
          {destaques.map((projeto) => (
            <article key={projeto.nome} className="rounded-3xl border border-zinc-800 bg-zinc-900 p-8">
              <span className="font-bold tracking-widest text-orange-500">{projeto.tipo}</span>
              <h3 className="mt-3 text-3xl font-black">{projeto.nome}</h3>
              <p className="mt-5 leading-7 text-zinc-400">{projeto.descricao}</p>
              <div className="mt-6 flex flex-wrap gap-2">
                {projeto.tecnologias.map((tecnologia) => <span key={tecnologia} className="rounded-xl bg-zinc-800 px-3 py-2 text-sm">{tecnologia}</span>)}
              </div>
              <a href={projeto.github} target="_blank" rel="noreferrer" className="mt-8 inline-block rounded-xl bg-orange-500 px-6 py-3 font-bold hover:bg-orange-600">Ver no GitHub</a>
            </article>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-8 pb-24">
        <div className="flex items-end justify-between gap-4 mb-8">
          <div>
            <span className="font-semibold tracking-widest text-orange-500">GITHUB</span>
            <h2 className="mt-2 text-3xl font-bold">Projetos e Laboratório</h2>
            <p className="mt-2 text-zinc-400">Repositórios públicos atualizados diretamente do GitHub.</p>
          </div>
          <a href="https://github.com/AdrianoJesusDeveloper" target="_blank" rel="noreferrer" className="text-orange-500 font-bold">Ver todos →</a>
        </div>

        {loadingRepos ? (
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-8 text-zinc-400">Carregando projetos do GitHub...</div>
        ) : githubProjects.length === 0 ? (
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-8 text-zinc-400">Não foi possível carregar os projetos agora.</div>
        ) : (
          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
            {githubProjects.map((repo) => (
              <a key={repo.id} href={repo.html_url} target="_blank" rel="noreferrer" className="rounded-2xl border border-zinc-800 bg-zinc-900 p-5 transition hover:border-orange-500">
                <h3 className="font-bold text-lg break-words">{repo.name}</h3>
                <p className="mt-3 min-h-16 text-sm text-zinc-400">{repo.description || "Projeto do laboratório Data Driven Dojô."}</p>
                <div className="mt-4 flex items-center justify-between text-xs text-zinc-500">
                  <span>{repo.language || "Projeto"}</span>
                  <span>★ {repo.stargazers_count}</span>
                </div>
              </a>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
