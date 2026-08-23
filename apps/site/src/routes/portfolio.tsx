import { createFileRoute } from "@tanstack/react-router";
import { Navbar } from "../components/Navbar";
import { ProjectCard } from "../components/ProjectCard";
import { projects } from "../data/projects";

export function Portfolio() {
  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <Navbar />
      <main className="mx-auto max-w-7xl px-8 py-20">
        <div className="mb-16">
          <span className="text-orange-500 font-bold tracking-[6px]">PORTFÓLIO</span>
          <h1 className="mt-4 text-6xl font-black">Projetos que constroem a jornada</h1>
          <p className="mt-6 max-w-3xl text-xl text-zinc-400 leading-8">
            Uma vitrine profissional da jornada de Adriano em Dados, Ciência de Dados,
            Inteligência Artificial, Cloud e desenvolvimento Full Stack. Cada projeto
            aponta para seu código público quando disponível.
          </p>
        </div>

        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <ProjectCard
              key={project.id}
              title={project.title}
              description={project.description}
              image={project.image}
              technologies={project.technologies}
              github={project.github}
              demo={project.demo}
              featured={project.featured}
            />
          ))}
        </div>
      </main>
    </div>
  );
}

export const Route = createFileRoute("/portfolio")({
  component: Portfolio,
});
