// import { Footer } from "../components/Footer";
import { Navbar } from "../components/Navbar";
export function HomePage() {
  return (
    <main>

      <Navbar />

      <section className="mx-auto max-w-7xl px-8 py-24">

        <span className="text-orange-500 font-bold tracking-widest">
          DATA DRIVEN DOJO
        </span>

        <h1 className="mt-6 text-7xl font-black leading-tight">
          Aprenda Dados
          <br />
          Construindo Projetos Reais
        </h1>

        <p className="mt-8 max-w-3xl text-xl text-zinc-400 leading-9">
          Transforme conhecimento em experiência prática através de
          projetos completos de Engenharia de Dados,
          Ciência de Dados,
          Inteligência Artificial,
          Business Intelligence
          e Desenvolvimento Full Stack.
        </p>
        {/* <Footer /> */}

      </section>

    </main>
  );
}