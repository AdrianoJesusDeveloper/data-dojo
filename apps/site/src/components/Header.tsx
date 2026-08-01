export function Header() {
  return (
    <header className="border-b border-zinc-800">

      <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-8">

        <h1 className="text-2xl font-black text-orange-500">
          DATA DRIVEN DOJO
        </h1>

        <nav className="flex gap-8">

          <a href="/">Home</a>

          <a href="/portfolio">Portfolio</a>

          <a href="/blog">Blog</a>

          <a href="/sobre">Sobre</a>

          <a href="/contato">Contato</a>

        </nav>

      </div>

    </header>
  );
}