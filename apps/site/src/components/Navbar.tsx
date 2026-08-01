import { Link } from "@tanstack/react-router";

export function Navbar() {
  return (
    <header className="border-b border-zinc-800">

      <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-8">

        <Link
          to="/"
          className="text-2xl font-black text-orange-500"
        >
          ADRIANO JESUS
        </Link>

        <nav className="flex gap-8">

          <Link to="/">
            Home
          </Link>

          <Link to="/portfolio">
            Projetos
          </Link>

          <a
            href="https://github.com/AdrianoJesusDeveloper"
            target="_blank"
          >
            GitHub
          </a>

          <a
            href="https://linkedin.com"
            target="_blank"
          >
            LinkedIn
          </a>

        </nav>

      </div>

    </header>
  );
}
