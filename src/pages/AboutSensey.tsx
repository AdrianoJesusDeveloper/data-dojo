import { DojoHeader } from "@/components/DojoHeader";

interface Profile { username: string; profile_picture: string | null; xp_points: number; }

const LINKEDIN_PROFILE_PHOTO = "https://media.licdn.com/dms/image/v2/D4D03AQF8z0S5V7ABQA/profile-displayphoto-crop_800_800/B4DZyCJA00JIAI-/0/1771709929215?e=1788998400&v=beta&t=rObBy-DXszDMhXiNU3GMVLUBg_BifW0Uth3CbDq0BXY";
const competencias = ["Python", "SQL", "Data Science", "Data Engineering", "IA", "Cloud Computing", "AWS", "Power BI"];

export default function AboutSensey() {
  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <DojoHeader />
      <main className="mx-auto max-w-6xl px-8 py-16">
        <section className="flex flex-col gap-8 md:flex-row md:items-center">
          <div className="h-36 w-36 shrink-0 overflow-hidden rounded-full border-2 border-orange-500 bg-zinc-900">
            <img
              src={LINKEDIN_PROFILE_PHOTO}
              alt="Adriano Jesus da Costa — Sensei do Data Driven Dojô"
              className="h-full w-full object-cover"
            />
          </div>
          <div>
            <span className="font-semibold tracking-widest text-orange-500">CONHEÇA O SENSEY</span>
            <h1 className="mt-3 text-5xl font-black">Adriano Jesus da Costa</h1>
            <p className="mt-4 max-w-3xl text-xl text-zinc-400">Profissional de tecnologia, dados e aprendizagem contínua. Criador do Data Driven Dojô e defensor da filosofia Kaizen: evoluir um pouco todos os dias.</p>
            <div className="mt-6 flex flex-wrap gap-3"><a href="https://www.linkedin.com/in/adriano-jesus-costa/" target="_blank" rel="noreferrer" className="rounded-xl bg-orange-500 px-5 py-3 font-bold">LinkedIn</a><a href="https://github.com/AdrianoJesusDeveloper" target="_blank" rel="noreferrer" className="rounded-xl border border-zinc-700 px-5 py-3 font-bold">GitHub</a></div>
          </div>
        </section>

        <section className="mt-16 grid gap-8 md:grid-cols-2">
          <article className="rounded-2xl border border-zinc-800 bg-zinc-900 p-7"><h2 className="text-2xl font-bold">Minha jornada</h2><p className="mt-4 leading-8 text-zinc-400">Formação em Sistemas de Informação, especialização em Big Data e Inteligência Competitiva e uma trajetória construída entre atendimento, tecnologia, dados, cloud e educação. O Dojô nasceu para transformar essa jornada em um ambiente onde outras pessoas também possam aprender, praticar e construir projetos reais.</p></article>
          <article className="rounded-2xl border border-zinc-800 bg-zinc-900 p-7"><h2 className="text-2xl font-bold">A filosofia do Dojô</h2><p className="mt-4 leading-8 text-zinc-400">Determinação, Disciplina e Dedicação. A Inteligência Artificial entra como parceira de evolução, não como substituta do raciocínio. O objetivo é formar profissionais capazes de entender, construir, testar e explicar aquilo que fazem.</p></article>
        </section>

        <section className="mt-10 rounded-2xl border border-zinc-800 bg-zinc-900 p-7"><h2 className="text-2xl font-bold">Arsenal técnico</h2><div className="mt-5 flex flex-wrap gap-3">{competencias.map((item) => <span key={item} className="rounded-xl bg-zinc-800 px-4 py-2 text-sm">{item}</span>)}</div></section>
      </main>
    </div>
  );
}
