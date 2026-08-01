type Props = {
  title: string;
  description: string;
  image: string;
  technologies: string[];
  github: string;
  demo: string;
  featured: boolean;
};

export function ProjectCard({
  title,
  description,
  image,
  technologies,
  github,
  demo,
  featured,
}: Props) {
  return (
    <article className="group overflow-hidden rounded-3xl border border-zinc-800 bg-zinc-900 transition duration-300 hover:-translate-y-2 hover:border-orange-500">

      <div className="relative overflow-hidden">

        {featured && (
          <span className="absolute left-4 top-4 z-10 rounded-full bg-orange-500 px-4 py-2 text-sm font-bold text-white">
            Destaque
          </span>
        )}

        <img
          src={image}
          alt={title}
          className="h-64 w-full object-cover transition duration-500 group-hover:scale-110"
        />

      </div>

      <div className="p-8">

        <h2 className="text-3xl font-black">
          {title}
        </h2>

        <p className="mt-5 leading-8 text-zinc-400">
          {description}
        </p>

        <div className="mt-6 flex flex-wrap gap-2">
          {technologies.map((tech) => (
            <span
              key={tech}
              className="rounded-lg bg-zinc-800 px-3 py-2 text-sm"
            >
              {tech}
            </span>
          ))}
        </div>

        <div className="mt-8 flex gap-4">

          <a
            href={github}
            target="_blank"
            rel="noreferrer"
            className="flex-1 rounded-xl bg-orange-500 py-3 text-center font-bold transition hover:bg-orange-600"
          >
            GitHub
          </a>

          <a
            href={demo}
            target="_blank"
            rel="noreferrer"
            className="flex-1 rounded-xl border border-zinc-700 py-3 text-center transition hover:border-orange-500"
          >
            Demo
          </a>

        </div>

      </div>

    </article>
  );
}