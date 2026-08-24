import { Link, createFileRoute } from "@tanstack/react-router";
import { ArrowRight, BookOpen, Database, Instagram, Linkedin, Menu, Search, ShoppingBag, Sparkles, UserRound, LogIn, UserPlus, KeyRound, X } from "lucide-react";
import { useEffect, useState } from "react";
import logoDojo from "../assets/logo_transparente.png";
import { api } from "../lib/api";

export const Route = createFileRoute("/store")({ component: StorePage });

type ApiProduct = {
  id: number;
  name: string;
  slug: string;
  short_description: string;
  description: string;
  product_type: "digital" | "physical" | "service";
  price: string;
  compare_at_price: string | null;
  image_url: string;
  featured: boolean;
  category: { id: number; name: string; slug: string; description: string };
};

type CartItem = { id: number; title: string; price: number; quantity: number };

function productIcon(type: ApiProduct["product_type"]) {
  if (type === "physical") return ShoppingBag;
  if (type === "service") return Sparkles;
  return BookOpen;
}

function StorePage() {
  const [products, setProducts] = useState<ApiProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [catalogError, setCatalogError] = useState("");
  const [cart, setCart] = useState<CartItem[]>([]);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [cartOpen, setCartOpen] = useState(false);

  useEffect(() => {
    try { setCart(JSON.parse(localStorage.getItem("ddj-store-cart") || "[]")); } catch { setCart([]); }
    api.get<ApiProduct[]>("/api/store/products/")
      .then(({ data }) => setProducts(Array.isArray(data) ? data : (data as unknown as { results: ApiProduct[] }).results || []))
      .catch(() => setCatalogError("Não foi possível carregar o catálogo agora. Tente novamente em instantes."))
      .finally(() => setLoading(false));
  }, []);

  const saveCart = (next: CartItem[]) => { setCart(next); localStorage.setItem("ddj-store-cart", JSON.stringify(next)); };
  const addToCart = (product: ApiProduct) => {
    const price = Number(product.price);
    const found = cart.find(i => i.id === product.id);
    saveCart(found ? cart.map(i => i.id === product.id ? { ...i, quantity: i.quantity + 1 } : i) : [...cart, { id: product.id, title: product.name, price, quantity: 1 }]);
    setCartOpen(true);
  };
  const removeFromCart = (id: number) => saveCart(cart.filter(i => i.id !== id));
  const totalItems = cart.reduce((s, i) => s + i.quantity, 0);
  const total = cart.reduce((s, i) => s + i.price * i.quantity, 0);

  return <div className="min-h-screen bg-background text-foreground">
    <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3 sm:px-6">
        <Link to="/store" className="flex shrink-0 items-center gap-3"><img src={logoDojo} alt="Data Driven Dojô" className="h-10 w-10 object-contain" /><div className="leading-tight"><div className="font-display text-lg font-bold">3DStore</div><div className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">Data Driven Dojô</div></div></Link>
        <nav className="ml-4 hidden items-center gap-1 md:flex"><a href="#catalogo" className="rounded-lg px-3 py-2 text-sm hover:bg-secondary">Produtos</a><a href="#categorias" className="rounded-lg px-3 py-2 text-sm hover:bg-secondary">Categorias</a><a href="#ofertas" className="rounded-lg px-3 py-2 text-sm hover:bg-secondary">Ofertas</a><Link to="/" className="rounded-lg px-3 py-2 text-sm hover:bg-secondary">Dojô</Link></nav>
        <div className="ml-auto flex items-center gap-2">
          <div className="hidden items-center gap-1 rounded-lg border border-border p-1 lg:flex"><Link to="/login" className="inline-flex items-center gap-1.5 rounded-md px-3 py-2 text-xs font-semibold hover:bg-secondary"><LogIn className="h-3.5 w-3.5" /> Entrar</Link><Link to="/register" className="inline-flex items-center gap-1.5 rounded-md bg-kaizen px-3 py-2 text-xs font-bold text-kaizen-foreground hover:brightness-110"><UserPlus className="h-3.5 w-3.5" /> Criar conta</Link></div>
          <Link to="/login" className="hidden h-10 w-10 items-center justify-center rounded-lg border border-border hover:bg-secondary sm:inline-flex lg:hidden" aria-label="Entrar"><UserRound className="h-4 w-4" /></Link>
          <button aria-label="Buscar" className="hidden h-10 w-10 items-center justify-center rounded-lg border border-border hover:bg-secondary sm:inline-flex"><Search className="h-4 w-4" /></button>
          <button onClick={() => setCartOpen(true)} aria-label="Abrir carrinho" className="relative flex h-10 items-center gap-2 rounded-lg border border-kaizen/40 bg-kaizen/10 px-3 text-kaizen hover:bg-kaizen/20"><ShoppingBag className="h-5 w-5" /><span className="hidden sm:inline">Carrinho</span>{totalItems > 0 && <span className="absolute -right-2 -top-2 flex h-5 min-w-5 items-center justify-center rounded-full bg-kaizen px-1 text-[11px] font-bold text-kaizen-foreground">{totalItems}</span>}</button>
          <button onClick={() => setMobileOpen(!mobileOpen)} className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-border md:hidden">{mobileOpen ? <X /> : <Menu />}</button>
        </div>
      </div>
      {mobileOpen && <nav className="border-t border-border px-4 py-3 md:hidden"><div className="flex flex-col gap-1"><a href="#catalogo" onClick={() => setMobileOpen(false)} className="rounded-lg px-3 py-2 hover:bg-secondary">Produtos</a><a href="#categorias" onClick={() => setMobileOpen(false)} className="rounded-lg px-3 py-2 hover:bg-secondary">Categorias</a><a href="#ofertas" onClick={() => setMobileOpen(false)} className="rounded-lg px-3 py-2 hover:bg-secondary">Ofertas</a><Link to="/login" onClick={() => setMobileOpen(false)} className="flex items-center gap-2 rounded-lg px-3 py-2 hover:bg-secondary"><LogIn className="h-4 w-4" /> Entrar</Link><Link to="/register" onClick={() => setMobileOpen(false)} className="flex items-center gap-2 rounded-lg bg-kaizen px-3 py-2 font-bold text-kaizen-foreground"><UserPlus className="h-4 w-4" /> Criar conta</Link><Link to="/recuperar-senha" onClick={() => setMobileOpen(false)} className="flex items-center gap-2 rounded-lg px-3 py-2 hover:bg-secondary"><KeyRound className="h-4 w-4" /> Recuperar senha</Link><Link to="/" onClick={() => setMobileOpen(false)} className="rounded-lg px-3 py-2 hover:bg-secondary">Voltar ao Dojô</Link></div></nav>}
    </header>

    <main>
      <section className="relative overflow-hidden border-b border-border bg-grid-dojo"><div className="absolute inset-0 bg-[radial-gradient(circle_at_75%_20%,rgba(255,165,0,.14),transparent_32%),radial-gradient(circle_at_20%_80%,rgba(0,87,184,.12),transparent_32%)]" /><div className="relative mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:py-28"><div className="max-w-4xl"><div className="mb-5 inline-flex items-center gap-2 rounded-full border border-kaizen/30 bg-kaizen/10 px-4 py-2 font-mono text-xs font-bold uppercase tracking-[0.18em] text-kaizen"><ShoppingBag className="h-4 w-4" />3DStore · Data Driven Dojô</div><h1 className="font-display text-5xl font-extrabold leading-[1.02] tracking-tight sm:text-6xl lg:text-7xl">Equipamentos para sua<span className="block text-kaizen text-glow-kaizen">jornada de evolução.</span></h1><p className="mt-7 max-w-2xl text-lg leading-8 text-muted-foreground sm:text-xl">Conhecimento, ferramentas e produtos para quem escolheu evoluir com <strong className="text-foreground">Determinação, Disciplina e Direção.</strong></p><div className="mt-9 flex flex-wrap gap-3"><a href="#catalogo" className="inline-flex items-center gap-2 rounded-xl bg-kaizen px-6 py-3.5 font-display font-bold text-kaizen-foreground transition hover:brightness-110">Explorar catálogo <ArrowRight className="h-4 w-4" /></a><Link to="/conheca-sensey" className="rounded-xl border border-border px-6 py-3.5 font-display font-bold transition hover:bg-secondary">Conhecer o Sensey</Link></div></div></div></section>

      <section id="categorias" className="mx-auto max-w-7xl px-4 py-8 sm:px-6"><div className="grid gap-3 sm:grid-cols-3"><a href="#catalogo" className="rounded-xl border border-border bg-card p-4 hover:border-kaizen/50"><span className="font-mono text-xs text-kaizen">01</span><strong className="mt-1 block font-display">E-books & Guias</strong></a><a href="#catalogo" className="rounded-xl border border-border bg-card p-4 hover:border-kaizen/50"><span className="font-mono text-xs text-kaizen">02</span><strong className="mt-1 block font-display">Templates & Dados</strong></a><a href="#catalogo" className="rounded-xl border border-border bg-card p-4 hover:border-kaizen/50"><span className="font-mono text-xs text-kaizen">03</span><strong className="mt-1 block font-display">IA & Automação</strong></a></div></section>

      <section id="catalogo" className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:py-16">
        <div className="mb-10 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"><div><p className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-kaizen">Catálogo</p><h2 className="mt-2 font-display text-3xl font-bold sm:text-4xl">Recursos para entrar em ação</h2></div><p className="max-w-md text-sm leading-6 text-muted-foreground">O catálogo é administrado pelo Django Admin. Cadastre um produto e ele aparecerá aqui automaticamente.</p></div>
        {loading ? <div className="rounded-2xl border border-border bg-card p-12 text-center text-muted-foreground">Carregando catálogo do Dojô...</div> : catalogError ? <div className="rounded-2xl border border-destructive/40 bg-destructive/10 p-8 text-center text-sm text-destructive">{catalogError}</div> : products.length === 0 ? <div className="rounded-2xl border border-dashed border-border bg-card p-12 text-center"><p className="font-display text-xl font-bold">Catálogo em preparação</p><p className="mt-2 text-sm text-muted-foreground">Nenhum produto ativo foi cadastrado ainda. Use o Django Admin para publicar o primeiro produto.</p><Link to="/login" className="mt-5 inline-flex rounded-xl border border-border px-5 py-3 font-semibold hover:bg-secondary">Entrar no Dojô</Link></div> : <div className="grid gap-5 md:grid-cols-3">{products.map(product => { const Icon = productIcon(product.product_type); return <article key={product.id} className="group overflow-hidden rounded-2xl border border-border bg-card transition hover:-translate-y-1 hover:border-kaizen/50">{product.image_url ? <img src={product.image_url} alt={product.name} className="h-48 w-full object-cover" /> : <div className="flex h-40 items-center justify-center bg-secondary text-kaizen"><Icon className="h-12 w-12" /></div>}<div className="p-6"><div className="flex items-center justify-between"><span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{product.category?.name || "Dojô"}</span>{product.featured && <span className="rounded-full bg-kaizen/10 px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-kaizen">Destaque</span>}</div><h3 className="mt-3 font-display text-2xl font-bold">{product.name}</h3><p className="mt-3 min-h-16 text-sm leading-6 text-muted-foreground">{product.short_description || product.description}</p><div className="mt-5 flex items-center justify-between"><strong className="font-display text-xl">R$ {Number(product.price).toFixed(2).replace('.', ',')}</strong><button onClick={() => addToCart(product)} className="rounded-xl bg-kaizen px-4 py-3 font-display font-bold text-kaizen-foreground hover:brightness-110">Adicionar</button></div></div></article>; })}</div>}
      </section>

      <section id="ofertas" className="border-y border-border bg-card"><div className="mx-auto max-w-7xl px-4 py-14 sm:px-6"><div className="grid gap-8 md:grid-cols-3">{[["01","Determinação","Você decide entrar no caminho."],["02","Disciplina","Você transforma intenção em prática."],["03","Direção","Você sabe qual é o próximo passo."]].map(([number,title,text]) => <div key={number} className="border-l-2 border-kaizen pl-5"><div className="font-mono text-xs text-kaizen">{number}</div><h3 className="mt-2 font-display text-xl font-bold">{title}</h3><p className="mt-1 text-sm text-muted-foreground">{text}</p></div>)}</div></div></section>
    </main>

    {cartOpen && <div className="fixed inset-0 z-50"><button aria-label="Fechar carrinho" onClick={() => setCartOpen(false)} className="absolute inset-0 bg-black/60" /><aside className="absolute right-0 top-0 flex h-full w-full max-w-md flex-col border-l border-border bg-background shadow-2xl"><div className="flex items-center justify-between border-b border-border p-5"><div><p className="font-mono text-xs uppercase text-kaizen">3DStore</p><h2 className="font-display text-2xl font-bold">Seu carrinho</h2></div><button onClick={() => setCartOpen(false)} className="rounded-lg p-2 hover:bg-secondary"><X /></button></div><div className="flex-1 overflow-y-auto p-5">{cart.length === 0 ? <div className="py-16 text-center text-muted-foreground">Seu carrinho está vazio.</div> : <div className="space-y-4">{cart.map(item => <div key={item.id} className="flex items-start justify-between gap-4 rounded-xl border border-border p-4"><div><p className="font-display font-bold">{item.title}</p><p className="mt-1 text-sm text-muted-foreground">Qtd. {item.quantity}</p></div><div className="text-right"><strong>R$ {(item.price * item.quantity).toFixed(2).replace('.', ',')}</strong><button onClick={() => removeFromCart(item.id)} className="mt-2 block text-xs text-destructive hover:underline">Remover</button></div></div>)}</div>}</div><div className="border-t border-border p-5"><div className="flex justify-between font-display text-xl font-bold"><span>Total</span><span className="text-kaizen">R$ {total.toFixed(2).replace('.', ',')}</span></div><Link to="/store/checkout" onClick={() => setCartOpen(false)} className={`mt-4 flex w-full items-center justify-center rounded-xl bg-kaizen px-5 py-4 font-display font-bold text-kaizen-foreground ${cart.length === 0 ? "pointer-events-none opacity-40" : ""}`}>Ir para checkout</Link></div></aside></div>}

    <footer className="border-t border-border bg-background"><div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-10 sm:flex-row sm:items-center sm:justify-between sm:px-6"><div><div className="font-display text-lg font-bold">Data Driven Dojô · 3DStore</div><p className="mt-1 text-sm text-muted-foreground">Determinação · Disciplina · Direção</p><p className="mt-2 text-xs text-muted-foreground">Conheça, acompanhe e compartilhe a jornada do Dojô.</p></div><div className="flex flex-wrap gap-3"><a href="https://www.instagram.com/p/Da0A28uETmK/" target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm hover:border-kaizen/50"><Instagram className="h-4 w-4" /> Instagram</a><a href="https://www.linkedin.com/in/data-driven-dojo-3ds/" target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm hover:border-kaizen/50"><Linkedin className="h-4 w-4" /> LinkedIn</a></div></div></footer>
  </div>;
}
