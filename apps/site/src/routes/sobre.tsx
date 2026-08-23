import { createFileRoute } from "@tanstack/react-router";
import { Navbar } from "../components/Navbar";

const linkedinUrl = "https://www.linkedin.com/in/adriano-jesus-costa/";
const githubUrl = "https://github.com/AdrianoJesusDeveloper";

const profile = {
  name: "Adriano Jesus Costa",
  headline: "Dados, Inteligência Artificial, Cloud e desenvolvimento de soluções digitais",
  summary:
    "Bacharel em Sistemas de Informação e profissional em evolução contínua na área de Dados e Inteligência Artificial. Minha jornada combina experiência prática em operações e atendimento, formação em Ciência de Dados e Big Data, Cloud Computing e construção de produtos digitais.",
  philosophy:
    "Acredito em aprendizado contínuo, prática orientada a projetos e evolução de 1% ao dia. O Data Driven Dojô nasceu dessa filosofia: transformar conhecimento em prática e prática em capacidade profissional.",
};

const strengths = [
  "Ciência e Análise de Dados",
  "Python e SQL",
  "Business Intelligence e Power BI",
  "Data Engineering e Big Data",
  "Inteligência Artificial e agentes de IA",
  "Cloud Computing e AWS",
  "APIs, Django e desenvolvimento Full Stack",
];

const journey = [
  {
    title: "Fundação",
    text: "Sistemas de Informação e experiência profissional em operações, atendimento e suporte, aproximando tecnologia das necessidades reais do negócio.",
  },
  {
    title: "Dados",
    text: "Formação em Ciência de Dados e especialização em Big Data e Inteligência Competitiva, com foco em Python, SQL, BI, engenharia e análise.",
  },
  {
    title: "Cloud & IA",
    text: "Evolução para Cloud Computing, AWS, desenvolvimento de aplicações e integração de Inteligência Artificial em produtos reais.",
  },
  {
    title: "Data Driven Dojô",
    text: "Um laboratório vivo para aprender, ensinar e construir: educação orientada a projetos, comunidade, Kaizen e agentes de IA acompanhando a jornada do aluno.",
  },
];

export function Sobre() {
  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <Navbar />

      <main className="mx-auto max-w-7xl px-8 py-20">
        <section className="max-w-5xl">
          <span className="text-orange-500 font-bold tracking-[6px]">CONHEÇA O SENSEY</span>
          <h1 className="mt-4 text-5xl font-black md:text-6xl">{profile.name}</h1>
          <p className="mt-5 text-xl text-orange-400">{profile.headline}</p>
          <p className="mt-7 max-w-4xl text-lg leading-8 text-zinc-300">{profile.summary}</p>

          <div className="mt-8 flex flex-wrap gap-4">
            <a className="rounded-lg border border-zinc-700 px-5 py-3 hover:border-orange-500" href={linkedinUrl} target="_blank" rel="noreferrer">LinkedIn</a>
            <a className="rounded-lg border border-zinc-700 px-5 py-3 hover:border-orange-500" href={githubUrl} target="_blank" rel="noreferrer">GitHub</a>
          </div>
        </section>

        <section className="mt-20 grid gap-8 lg:grid-cols-2">
          <div>
            <span className="text-orange-500 font-bold tracking-[4px]">A JORNADA</span>
            <div className="mt-8 space-y-6">
              {journey.map((item) => (
                <article key={item.title} className="border-l border-zinc-700 pl-6">
                  <h2 className="text-2xl font-bold">{item.title}</h2>
                  <p className="mt-2 leading-7 text-zinc-400">{item.text}</p>
                </article>
              ))}
            </div>
          </div>

          <div>
            <span className="text-orange-500 font-bold tracking-[4px]">ÁREAS DE ATUAÇÃO</span>
            <div className="mt-8 grid gap-3 sm:grid-cols-2">
              {strengths.map((strength) => (
                <div key={strength} className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4 text-zinc-200">{strength}</div>
              ))}
            </div>

            <div className="mt-10 rounded-xl border border-zinc-800 p-6">
              <h2 className="text-2xl font-bold">A filosofia do Dojô</h2>
              <p className="mt-3 leading-7 text-zinc-400">{profile.philosophy}</p>
            </div>
          </div>
        </section>

        <section className="mt-24">
          <div className="flex flex-col justify-between gap-5 md:flex-row md:items-end">
            <div>
              <span className="text-orange-500 font-bold tracking-[4px]">PORTFÓLIO</span>
              <h2 className="mt-3 text-4xl font-black">Projetos que mostram a jornada</h2>
              <p className="mt-4 max-w-3xl text-zinc-400 leading-7">O portfólio do Dojô também funciona como vitrine profissional: projetos reais, código público e tecnologias utilizadas em cada solução.</p>
            </div>
            <a className="whitespace-nowrap rounded-lg border border-orange-500 px-5 py-3 text-orange-400 hover:bg-orange-500 hover:text-black" href="/portfolio">Ver portfólio completo</a>
          </div>
        </section>
      </main>
    </div>
  );
}

export const Route = createFileRoute("/sobre")({
  component: Sobre,
});
