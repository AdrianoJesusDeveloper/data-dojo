import { DojoHeader } from "@/components/DojoHeader";



const projetos = [
  {
    id: 1,
    nome: "DojoMart",
    tipo: "PROJETO 01",
    descricao:
      "Plataforma completa para gestão de supermercados desenvolvida no Data Driven Dojo. Possui arquitetura Full Stack utilizando React, Django, PostgreSQL, Docker, Power BI e APIs REST.",
    imagem: "https://placehold.co/800x500/18181b/f97316?text=DojoMart",
    tecnologias: [
      "React",
      "Django",
      "PostgreSQL",
      "Docker",
      "Power BI",
      "Python",
    ],
  },
];

export default function PortfolioPage() {
  return (
    <div className="min-h-screen bg-zinc-950 text-white">

      <DojoHeader />

      {/* HERO */}
      <section className="mx-auto max-w-7xl px-8 py-24">

        <span className="text-orange-500 font-semibold tracking-widest">
          DATA DRIVEN DOJO
        </span>

        <h1 className="mt-4 text-6xl font-black">
          Portfólio de Projetos
        </h1>

        <p className="mt-6 max-w-3xl text-zinc-400 text-xl">
          Projetos completos de Engenharia de Dados,
          Business Intelligence,
          Ciência de Dados,
          Inteligência Artificial
          e Desenvolvimento Full Stack.
        </p>

        <button className="mt-10 rounded-xl bg-orange-500 px-8 py-4 text-lg font-bold hover:bg-orange-600 transition">
          Explorar Projetos
        </button>

      </section>

      {/* PROJETOS */}
      <section className="mx-auto max-w-7xl px-8 pb-24">

        <h2 className="mb-12 text-4xl font-bold">
          Projetos em Destaque
        </h2>

        <div className="space-y-16">

          {projetos.map((projeto) => (

            <div
              key={projeto.id}
              className="grid items-center gap-12 rounded-3xl border border-zinc-800 bg-zinc-900 p-10 lg:grid-cols-2"
            >

              <div>

                <img
                  src={projeto.imagem}
                  alt={projeto.nome}
                  className="w-full rounded-2xl"
                />

              </div>

              <div>

                <span className="font-bold tracking-widest text-orange-500">
                  {projeto.tipo}
                </span>

                <h3 className="mt-3 text-5xl font-black">
                  {projeto.nome}
                </h3>

                <p className="mt-6 leading-8 text-zinc-400">
                  {projeto.descricao}
                </p>

                <div className="mt-8 flex flex-wrap gap-3">

                  {projeto.tecnologias.map((tec) => (

                    <span
                      key={tec}
                      className="rounded-xl bg-zinc-800 px-4 py-2"
                    >
                      {tec}
                    </span>

                  ))}

                </div>

                <div className="mt-10 flex gap-4">

                  <button className="rounded-xl bg-orange-500 px-8 py-4 font-bold transition hover:bg-orange-600">
                    Ver Projeto
                  </button>

                  <button className="rounded-xl border border-zinc-700 px-8 py-4 transition hover:border-orange-500">
                    GitHub
                  </button>

                </div>

              </div>

            </div>

          ))}

        </div>

      </section>

    </div>
  );
}