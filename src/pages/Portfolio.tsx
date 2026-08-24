import { useEffect, useState } from "react";
import { ExternalLink, Github, Globe2, Instagram, Linkedin, Plus, Star, Trash2 } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { toast, Toaster } from "sonner";
import { DojoHeader } from "@/components/DojoHeader";
import { api, getAuthToken } from "@/lib/api";

type Course = { id: number; title: string };
type GithubRepo = { id: number; name: string; html_url: string; description: string | null; language: string | null; stargazers_count: number; fork: boolean };
type Student = { id: number; username: string; profile_picture: string | null; xp_points: number; github_url: string; linkedin_url: string; instagram_url: string; website_url: string };
type Project = { id: number; student: Student; course: number; course_title: string; title: string; summary: string; description: string; technologies: string[]; repository_url: string; demo_url: string; image_url: string; status: "draft" | "published"; featured: boolean; is_owner: boolean; updated_at: string };
type ProjectForm = { course: string; title: string; summary: string; description: string; technologies: string; repository_url: string; demo_url: string; image_url: string; status: "draft" | "published" };

const initialForm: ProjectForm = { course: "", title: "", summary: "", description: "", technologies: "", repository_url: "", demo_url: "", image_url: "", status: "published" };
const list = <T,>(data: T[] | { results: T[] }) => Array.isArray(data) ? data : data.results || [];
const founderHighlights = [
  { title: "Data Driven Dojô", type: "PROJETO PRINCIPAL", summary: "Plataforma educacional criada para unir aprendizagem, dados, IA, comunidade e evolução Kaizen em uma única experiência.", technologies: ["React", "TypeScript", "Django", "Python", "PostgreSQL", "IA"], url: "https://github.com/AdrianoJesusDeveloper/data-dojo" },
  { title: "Dashboard de DRE — SG Global Group", type: "DATA ANALYTICS", summary: "Dashboard orientado à análise da Demonstração do Resultado do Exercício para apoiar decisões gerenciais.", technologies: ["Python", "SQL", "Power BI", "Data Analytics"], url: "https://github.com/AdrianoJesusDeveloper/Dashboard_de_DRE_SG-Global_Group_DNC" },
];

export default function PortfolioPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [form, setForm] = useState<ProjectForm>(initialForm);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [courseFilter, setCourseFilter] = useState("");
  const [founderRepos, setFounderRepos] = useState<GithubRepo[]>([]);
  const [loadingFounderRepos, setLoadingFounderRepos] = useState(true);
  const authenticated = !!getAuthToken();

  async function load() {
    try {
      const [projectResponse, courseResponse] = await Promise.all([
        api.get<Project[] | { results: Project[] }>("/api/portfolio/projects/"),
        api.get<Course[] | { results: Course[] }>("/api/courses/"),
      ]);
      setProjects(list(projectResponse.data));
      setCourses(list(courseResponse.data));
    } catch { toast.error("Não foi possível carregar o portfólio."); }
    finally { setLoading(false); }
  }

  useEffect(() => {
    load();
    fetch("https://api.github.com/users/AdrianoJesusDeveloper/repos?per_page=30&sort=updated")
      .then((response) => response.ok ? response.json() : [])
      .then((data: GithubRepo[]) => setFounderRepos(data.filter((repo) => !repo.fork).slice(0, 8)))
      .catch(() => setFounderRepos([]))
      .finally(() => setLoadingFounderRepos(false));
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!form.course) { toast.error("Selecione a formação relacionada ao projeto."); return; }
    setSaving(true);
    try {
      const { data } = await api.post<Project>("/api/portfolio/projects/", {
        ...form,
        course: Number(form.course),
        technologies: form.technologies.split(",").map((item) => item.trim()).filter(Boolean),
      });
      setProjects((current) => [data, ...current]);
      setForm(initialForm);
      setShowForm(false);
      toast.success(data.status === "published" ? "Projeto publicado no portfólio." : "Projeto salvo como rascunho.");
    } catch (error: any) { toast.error(error?.response?.data?.detail || "Não foi possível salvar o projeto."); }
    finally { setSaving(false); }
  }

  async function remove(project: Project) {
    if (!window.confirm(`Excluir o projeto “${project.title}”?`)) return;
    try {
      await api.delete(`/api/portfolio/projects/${project.id}/`);
      setProjects((current) => current.filter((item) => item.id !== project.id));
      toast.success("Projeto excluído.");
    } catch { toast.error("Não foi possível excluir o projeto."); }
  }

  const visibleProjects = courseFilter ? projects.filter((project) => String(project.course) === courseFilter) : projects;

  return <div className="min-h-screen bg-background text-foreground"><DojoHeader /><Toaster position="top-right" theme="dark" richColors />
    <main className="mx-auto max-w-7xl px-4 py-14 sm:px-8">
      <section className="rounded-3xl border border-border bg-card p-7 sm:p-10"><div className="flex flex-col gap-7 lg:flex-row lg:items-end lg:justify-between"><div><span className="font-mono text-xs font-semibold uppercase tracking-[.2em] text-kaizen">Projetos das formações</span><h1 className="mt-4 max-w-4xl font-display text-4xl font-black sm:text-6xl">Portfólio dos alunos</h1><p className="mt-5 max-w-3xl text-lg text-muted-foreground">Uma vitrine dos projetos desenvolvidos pelos samurais durante as formações do Data Driven Dojô.</p></div>{authenticated ? <button onClick={() => setShowForm(!showForm)} className="inline-flex items-center justify-center gap-2 rounded-xl bg-kaizen px-5 py-3 font-bold text-kaizen-foreground"><Plus size={18} /> Adicionar projeto</button> : <Link to="/login" search={{ redirect: "/portfolio" }} className="rounded-xl border border-kaizen px-5 py-3 text-center font-bold text-kaizen">Entre para publicar</Link>}</div></section>

      {showForm && <form onSubmit={submit} className="mt-8 grid gap-4 rounded-3xl border border-border bg-card p-7 md:grid-cols-2"><div className="md:col-span-2"><h2 className="font-display text-2xl font-bold">Cadastrar projeto da formação</h2><p className="mt-1 text-sm text-muted-foreground">Use links públicos e descreva claramente o problema resolvido.</p></div>
        <label className="grid gap-2 text-sm">Formação<select required value={form.course} onChange={(e) => setForm({ ...form, course: e.target.value })} className="rounded-xl border border-border bg-background p-3"><option value="">Selecione uma formação</option>{courses.map((course) => <option key={course.id} value={course.id}>{course.title}</option>)}</select></label>
        <label className="grid gap-2 text-sm">Título<input required maxLength={180} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="rounded-xl border border-border bg-background p-3" /></label>
        <label className="grid gap-2 text-sm md:col-span-2">Resumo<input required maxLength={320} value={form.summary} onChange={(e) => setForm({ ...form, summary: e.target.value })} placeholder="O problema, a solução e o principal resultado" className="rounded-xl border border-border bg-background p-3" /></label>
        <label className="grid gap-2 text-sm md:col-span-2">Descrição<textarea rows={4} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="rounded-xl border border-border bg-background p-3" /></label>
        <label className="grid gap-2 text-sm md:col-span-2">Tecnologias<input value={form.technologies} onChange={(e) => setForm({ ...form, technologies: e.target.value })} placeholder="Python, SQL, Power BI (separadas por vírgula)" className="rounded-xl border border-border bg-background p-3" /></label>
        <label className="grid gap-2 text-sm">Repositório<input type="url" value={form.repository_url} onChange={(e) => setForm({ ...form, repository_url: e.target.value })} placeholder="https://github.com/..." className="rounded-xl border border-border bg-background p-3" /></label><label className="grid gap-2 text-sm">Demonstração<input type="url" value={form.demo_url} onChange={(e) => setForm({ ...form, demo_url: e.target.value })} placeholder="https://..." className="rounded-xl border border-border bg-background p-3" /></label>
        <label className="grid gap-2 text-sm md:col-span-2">Imagem de capa<input type="url" value={form.image_url} onChange={(e) => setForm({ ...form, image_url: e.target.value })} placeholder="URL pública da imagem" className="rounded-xl border border-border bg-background p-3" /></label>
        <label className="grid gap-2 text-sm">Visibilidade<select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value as ProjectForm["status"] })} className="rounded-xl border border-border bg-background p-3"><option value="published">Publicar agora</option><option value="draft">Salvar como rascunho</option></select></label><div className="flex items-end gap-3"><button disabled={saving} className="rounded-xl bg-kaizen px-5 py-3 font-bold text-kaizen-foreground disabled:opacity-50">{saving ? "Salvando..." : "Salvar projeto"}</button><button type="button" onClick={() => setShowForm(false)} className="rounded-xl border border-border px-5 py-3">Cancelar</button></div>
      </form>}

      <section className="py-12"><div className="mb-7 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div><h2 className="font-display text-3xl font-bold">Projetos da comunidade</h2><p className="mt-2 text-muted-foreground">Explore projetos por formação, tecnologias e desafios resolvidos.</p></div><select aria-label="Filtrar por formação" value={courseFilter} onChange={(e) => setCourseFilter(e.target.value)} className="rounded-xl border border-border bg-card px-4 py-3"><option value="">Todas as formações</option>{courses.map((course) => <option key={course.id} value={course.id}>{course.title}</option>)}</select></div>
        {loading ? <div className="rounded-2xl border border-border bg-card p-8 text-muted-foreground">Carregando projetos...</div> : visibleProjects.length === 0 ? <div className="rounded-2xl border border-border bg-card p-10 text-center"><h3 className="font-display text-xl font-bold">Nenhum projeto publicado nesta formação.</h3><p className="mt-2 text-muted-foreground">Os próximos projetos desenvolvidos pelos alunos aparecerão aqui.</p></div> : <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">{visibleProjects.map((project) => <article key={project.id} className="overflow-hidden rounded-2xl border border-border bg-card">{project.image_url ? <img src={project.image_url} alt="" className="h-48 w-full object-cover" /> : <div className="flex h-32 items-center justify-center bg-gradient-to-br from-primary/30 to-kaizen/10 font-mono text-sm uppercase tracking-widest text-kaizen">Projeto Kaizen</div>}<div className="p-6"><div className="flex items-center justify-between gap-3"><span className="font-mono text-xs uppercase tracking-wider text-kaizen">{project.course_title}</span>{project.featured && <Star size={16} className="text-kaizen" fill="currentColor" />}</div><h3 className="mt-3 font-display text-2xl font-bold">{project.title}</h3><p className="mt-3 text-sm leading-6 text-muted-foreground">{project.summary}</p><div className="mt-4 flex flex-wrap gap-2">{project.technologies.map((technology) => <span key={technology} className="rounded-lg bg-secondary px-2.5 py-1 text-xs">{technology}</span>)}</div><div className="mt-5 flex items-center gap-3"><div className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-full bg-secondary">{project.student.profile_picture ? <img src={project.student.profile_picture} alt="" className="h-full w-full object-cover" /> : project.student.username.slice(0, 1).toUpperCase()}</div><div><p className="text-sm font-bold">{project.student.username}</p><p className="text-xs text-muted-foreground">{project.student.xp_points} XP Kaizen</p></div>{project.status === "draft" && <span className="ml-auto rounded-full border border-border px-2 py-1 text-xs text-muted-foreground">Rascunho</span>}</div><div className="mt-4 flex flex-wrap gap-2">{project.student.github_url && <a href={project.student.github_url} target="_blank" rel="noreferrer" aria-label={`GitHub de ${project.student.username}`} className="rounded-lg border border-border p-2 text-muted-foreground hover:border-kaizen hover:text-kaizen"><Github size={16} /></a>}{project.student.linkedin_url && <a href={project.student.linkedin_url} target="_blank" rel="noreferrer" aria-label={`LinkedIn de ${project.student.username}`} className="rounded-lg border border-border p-2 text-muted-foreground hover:border-kaizen hover:text-kaizen"><Linkedin size={16} /></a>}{project.student.instagram_url && <a href={project.student.instagram_url} target="_blank" rel="noreferrer" aria-label={`Instagram de ${project.student.username}`} className="rounded-lg border border-border p-2 text-muted-foreground hover:border-kaizen hover:text-kaizen"><Instagram size={16} /></a>}{project.student.website_url && <a href={project.student.website_url} target="_blank" rel="noreferrer" aria-label={`Site de ${project.student.username}`} className="rounded-lg border border-border p-2 text-muted-foreground hover:border-kaizen hover:text-kaizen"><Globe2 size={16} /></a>}</div><div className="mt-5 flex flex-wrap gap-2">{project.repository_url && <a href={project.repository_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm hover:border-kaizen"><Github size={15} /> Código</a>}{project.demo_url && <a href={project.demo_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-lg bg-kaizen px-3 py-2 text-sm font-bold text-kaizen-foreground"><ExternalLink size={15} /> Ver projeto</a>}{project.is_owner && <button onClick={() => remove(project)} className="ml-auto rounded-lg p-2 text-destructive hover:bg-destructive/10" aria-label={`Excluir ${project.title}`}><Trash2 size={17} /></button>}</div></div></article>)}</div>}
      </section>

      <section className="border-t border-border py-14">
        <div className="mb-8 flex flex-col gap-5 md:flex-row md:items-end md:justify-between"><div><span className="font-mono text-xs font-semibold uppercase tracking-[.2em] text-kaizen">Portfólio do fundador</span><h2 className="mt-3 font-display text-4xl font-black">Projetos de Adriano Costa</h2><p className="mt-3 max-w-3xl text-muted-foreground">Engenharia de Dados, Business Intelligence, Ciência de Dados, IA, Cloud e desenvolvimento Full Stack.</p></div><div className="flex gap-3"><a href="https://www.linkedin.com/in/adriano-jesus-costa/" target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-xl bg-kaizen px-4 py-3 font-bold text-kaizen-foreground"><Linkedin size={17} /> LinkedIn</a><a href="https://github.com/AdrianoJesusDeveloper" target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-xl border border-border px-4 py-3 font-bold hover:border-kaizen"><Github size={17} /> GitHub</a></div></div>
        <div className="grid gap-6 lg:grid-cols-2">{founderHighlights.map((project) => <article key={project.title} className="rounded-3xl border border-border bg-card p-7"><span className="font-mono text-xs font-bold tracking-widest text-kaizen">{project.type}</span><h3 className="mt-3 font-display text-3xl font-black">{project.title}</h3><p className="mt-4 leading-7 text-muted-foreground">{project.summary}</p><div className="mt-5 flex flex-wrap gap-2">{project.technologies.map((technology) => <span key={technology} className="rounded-lg bg-secondary px-3 py-1.5 text-sm">{technology}</span>)}</div><a href={project.url} target="_blank" rel="noreferrer" className="mt-6 inline-flex items-center gap-2 rounded-xl border border-kaizen px-4 py-2 font-bold text-kaizen"><Github size={16} /> Ver no GitHub</a></article>)}</div>
        <div className="mt-12"><div className="mb-6 flex items-end justify-between"><div><h3 className="font-display text-2xl font-bold">Projetos e laboratório</h3><p className="mt-1 text-sm text-muted-foreground">Repositórios públicos atualizados diretamente do GitHub.</p></div><a href="https://github.com/AdrianoJesusDeveloper" target="_blank" rel="noreferrer" className="font-bold text-kaizen">Ver todos →</a></div>{loadingFounderRepos ? <div className="rounded-2xl border border-border bg-card p-7 text-muted-foreground">Carregando projetos do GitHub...</div> : founderRepos.length === 0 ? <div className="rounded-2xl border border-border bg-card p-7 text-muted-foreground">Não foi possível carregar os repositórios agora.</div> : <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">{founderRepos.map((repo) => <a key={repo.id} href={repo.html_url} target="_blank" rel="noreferrer" className="rounded-2xl border border-border bg-card p-5 transition hover:border-kaizen"><h4 className="break-words font-display text-lg font-bold">{repo.name}</h4><p className="mt-3 min-h-16 text-sm text-muted-foreground">{repo.description || "Projeto do laboratório Data Driven Dojô."}</p><div className="mt-4 flex justify-between text-xs text-muted-foreground"><span>{repo.language || "Projeto"}</span><span>★ {repo.stargazers_count}</span></div></a>)}</div>}</div>
      </section>
    </main>
  </div>;
}
