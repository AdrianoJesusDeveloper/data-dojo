export function About() {
  return (
    <section className="mx-auto max-w-7xl px-8 py-32">

      <div className="grid gap-16 lg:grid-cols-2 items-center">

        <div>

          <span className="text-orange-500 font-bold tracking-[6px]">
            SOBRE MIM
          </span>

          <h2 className="mt-6 text-5xl font-black">
            Transformando dados em soluções reais
          </h2>

          <p className="mt-8 text-zinc-400 leading-8 text-lg">
            Sou Adriano Jesus, Bacharel em Sistemas de Informação,
            Tecnólogo em Ciência de Dados e especialista em Big Data.
          </p>

          <p className="mt-6 text-zinc-400 leading-8 text-lg">
            Desenvolvo aplicações Full Stack, APIs REST, pipelines de dados,
            dashboards analíticos e soluções utilizando Inteligência Artificial.
          </p>

          <p className="mt-6 text-zinc-400 leading-8 text-lg">
            Também sou fundador do projeto Data Driven Dojo, cujo objetivo é
            formar profissionais preparados para resolver problemas de negócio
            utilizando dados.
          </p>

        </div>

        <div className="flex justify-center">

          <img
            src="/images/profile.jpg"
            alt="Adriano Jesus"
            className="w-96 rounded-3xl border border-zinc-800"
          />

        </div>

      </div>

    </section>
  );
}