import { Link, createFileRoute } from "@tanstack/react-router";
import { ArrowRight, BookOpen, Database, ShoppingBag, Sparkles, Trash2, Plus, Minus } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import logoDojo from "../assets/logo_transparente.png";
import { api } from "../lib/api";

export const Route = createFileRoute("/store")({ component: StorePage });

type Product = {
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

type CartItem = { id: number; product: Product; quantity: number; subtotal: string };

type Cart = { id: number; items: CartItem[]; total: string; updated_at: string };

const fallbackProducts: Product[] = [
  { id: 1, name: "Fundamentos para Dados", slug: "fundamentos-para-dados", short_description: "Base sólida em dados, Python e tecnologia.", description: "Materiais práticos para construir uma base sólida em dados, Python e tecnologia.", product_type: "digital", price: "0.00", compare_at_price: null, image_url: "", featured: true, category: { id: 1, name: "E-books & Guias", slug: "ebooks", description: "" } },
  { id: 2, name: "Kit Data Analyst", slug: "kit-data-analyst", short_description: "Templates, datasets e recursos para portfólio.", description: "Templates, datasets e recursos para acelerar seus projetos e portfólio profissional.", product_type: "digital", price: "0.00", compare_at_price: null, image_url: "", featured: false, category: { id: 2, name: "Templates & Dados", slug: "templates", description: "" } },
  { id: 3, name: "Kit IA para Produtividade", slug: "kit-ia-produtividade", short_description: "Prompts e recursos para aplicar IA com estratégia.", description: "Prompts, modelos e recursos para aplicar IA com mais estratégia no dia a dia.", product_type: "digital", price: "0.00", compare_at_price: null, image_url: "", featured: false, category: { id: 3, name: "IA & Automação", slug: "ia", description: "" } },
];

const iconForCategory = (category: string) => {
  if (category.toLowerCase().includes("ia")) return Sparkles;
  if (category.toLowerCase().includes("dados")) return Database;
  return BookOpen;
};

function StorePage() {
  const [products, setProducts] = useState<Product[]>(fallbackProducts);
  const [cart, setCart] = useState<Cart | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  useEffect(() => {
    api.get<Product[]>("/api/store/products/")
      .then(({ data }) => { if (Array.isArray(data)) setProducts(data); })
      .catch(() => setMessage("Catálogo demonstrativo. Cadastre os produtos no Admin para publicar a loja."))
      .finally(() => setLoading(false));
  }, []);

  const refreshCart = () => api.get<Cart>("/api/store/cart/").then(({ data }) => setCart(data)).catch(() => setCart(null));

  const addToCart = async (productId: number) => {
    try {
      const { data } = await api.post<Cart>("/api/store/cart/", { product_id: productId, quantity: 1 });
      setCart(data);
      setMessage("Produto adicionado ao carrinho.");
    } catch {
      setMessage("Entre no Dojô para adicionar produtos ao carrinho.");
    }
  };

  const updateQuantity = async (itemId: number, quantity: number) => {
    try {
      const { data } = await api.patch<Cart>("/api/store/cart/", { item_id: itemId, quantity });
      setCart(data);
    } catch { setMessage("Não foi possível atualizar o carrinho."); }
  };

  const removeItem = async (itemId: number) => {
    try {
      const { data } = await api.delete<Cart>("/api/store/cart/", { data: { item_id: itemId } });
      setCart(data);
    } catch { setMessage("Não foi possível remover o produto."); }
  };

  const cartCount = useMemo(() => cart?.items.reduce((sum, item) => sum + item.quantity, 0) ?? 0, [cart]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-30 border-b border-border bg-background/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <Link to="/" className="flex items-center gap-3">
            <img src={logoDojo} alt="Data Driven Dojô" className="h-10 w-10 object-contain" />
            <div className="leading-tight"><div className="font-display text-lg font-bold">Data Driven Dojô</div><div className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">3DStore</div></div>
          </Link>
          <div className="flex items-center gap-2">
            <button onClick={() => { refreshCart(); document.getElementById("carrinho")?.scrollIntoView({ behavior: "smooth" }); }} className="relative rounded-lg border border-border px-4 py-2 text-sm transition hover:bg-secondary">
              🛒 Carrinho{cartCount > 0 && <span className="ml-2 rounded-full bg-kaizen px-2 py-0.5 text-xs text-kaizen-foreground">{cartCount}</span>}
            </button>
            <Link to="/" className="hidden rounded-lg border border-border px-4 py-2 text-sm transition hover:bg-secondary sm:block">Voltar ao Dojô</Link>
          </div>
        </div>
      </header>

      <main>
        <section className="relative overflow-hidden border-b border-border bg-grid-dojo">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_75%_20%,rgba(255,165,0,.14),transparent_32%),radial-gradient(circle_at_20%_80%,rgba(0,87,184,.12),transparent_32%)]" />
          <div className="relative mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:py-28">
            <div className="max-w-4xl">
              <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-kaizen/30 bg-kaizen/10 px-4 py-2 font-mono text-xs font-bold uppercase tracking-[0.18em] text-kaizen"><ShoppingBag className="h-4 w-4" />3DStore · Data Driven Dojô</div>
              <h1 className="font-display text-5xl font-extrabold leading-[1.02] tracking-tight sm:text-6xl lg:text-7xl">Equipamentos para sua<span className="block text-kaizen text-glow-kaizen">jornada de evolução.</span></h1>
              <p className="mt-7 max-w-2xl text-lg leading-8 text-muted-foreground sm:text-xl">Conhecimento, ferramentas e produtos para quem escolheu evoluir com <strong className="text-foreground">Determinação, Disciplina e Direção.</strong></p>
              <div className="mt-9 flex flex-wrap gap-3"><a href="#catalogo" className="inline-flex items-center gap-2 rounded-xl bg-kaizen px-6 py-3.5 font-display font-bold text-kaizen-foreground transition hover:brightness-110">Explorar catálogo <ArrowRight className="h-4 w-4" /></a><Link to="/" className="rounded-xl border border-border px-6 py-3.5 font-display font-bold transition hover:bg-secondary">Conhecer o Dojô</Link></div>
            </div>
          </div>
        </section>

        <section id="catalogo" className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:py-20">
          <div className="mb-10 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"><div><p className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-kaizen">Primeiro arsenal</p><h2 className="mt-2 font-display text-3xl font-bold sm:text-4xl">Recursos para entrar em ação</h2></div><p className="max-w-md text-sm leading-6 text-muted-foreground">Catálogo digital primeiro. Produtos físicos e serviços entram depois, aproveitando a mesma infraestrutura.</p></div>
          {message && <div className="mb-6 rounded-xl border border-kaizen/30 bg-kaizen/10 px-4 py-3 text-sm text-kaizen">{message}</div>}
          <div className="grid gap-5 md:grid-cols-3">
            {products.map((product) => { const Icon = iconForCategory(product.category.name); return (
              <article key={product.id} className="group overflow-hidden rounded-2xl border border-border bg-card transition hover:-translate-y-1 hover:border-kaizen/50 hover:shadow-[0_18px_50px_rgba(0,0,0,.25)]">
                {product.image_url ? <img src={product.image_url} alt={product.name} className="h-44 w-full object-cover" /> : <div className="flex h-44 items-center justify-center bg-secondary"><Icon className="h-14 w-14 text-kaizen" /></div>}
                <div className="p-6"><div className="flex items-center justify-between"><span className="rounded-full bg-secondary px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{product.product_type}</span>{product.featured && <span className="font-mono text-[10px] uppercase tracking-wider text-kaizen">Destaque</span>}</div><p className="mt-5 font-mono text-xs uppercase tracking-wider text-muted-foreground">{product.category.name}</p><h3 className="mt-2 font-display text-2xl font-bold">{product.name}</h3><p className="mt-3 min-h-12 text-sm leading-6 text-muted-foreground">{product.short_description || product.description}</p><div className="mt-6 flex items-center justify-between gap-3"><div className="font-display text-xl font-bold">{Number(product.price) > 0 ? `R$ ${Number(product.price).toFixed(2).replace('.', ',')}` : "Em breve"}</div><button disabled={Number(product.price) <= 0 || loading} onClick={() => addToCart(product.id)} className="rounded-xl bg-kaizen px-4 py-3 font-display font-bold text-kaizen-foreground transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50">Adicionar</button></div></div>
              </article>
            ); })}
          </div>
        </section>

        <section id="carrinho" className="border-y border-border bg-card"><div className="mx-auto max-w-7xl px-4 py-14 sm:px-6"><div className="flex items-center justify-between"><div><p className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-kaizen">Arsenal selecionado</p><h2 className="mt-2 font-display text-3xl font-bold">Seu carrinho</h2></div><button onClick={refreshCart} className="text-sm text-muted-foreground hover:text-foreground">Atualizar</button></div>{cart?.items.length ? <div className="mt-8 space-y-3">{cart.items.map((item) => <div key={item.id} className="flex items-center justify-between gap-4 rounded-xl border border-border bg-background p-4"><div className="min-w-0"><div className="font-semibold">{item.product.name}</div><div className="text-sm text-muted-foreground">R$ {Number(item.product.price).toFixed(2).replace('.', ',')}</div></div><div className="flex items-center gap-2"><button onClick={() => updateQuantity(item.id, item.quantity - 1)} className="rounded-md border p-2"><Minus className="h-4 w-4" /></button><span className="w-8 text-center">{item.quantity}</span><button onClick={() => updateQuantity(item.id, item.quantity + 1)} className="rounded-md border p-2"><Plus className="h-4 w-4" /></button><button onClick={() => removeItem(item.id)} className="rounded-md border p-2 text-samurai"><Trash2 className="h-4 w-4" /></button></div></div>)}<div className="flex items-center justify-between border-t border-border pt-5"><span className="font-display text-xl font-bold">Total</span><span className="font-display text-2xl font-bold text-kaizen">R$ {Number(cart.total).toFixed(2).replace('.', ',')}</span></div><Link to="/login" className="mt-4 inline-flex w-full items-center justify-center rounded-xl bg-kaizen px-6 py-3.5 font-display font-bold text-kaizen-foreground">Entrar para finalizar pedido</Link></div> : <p className="mt-6 text-sm text-muted-foreground">Seu carrinho está vazio. Escolha um produto para começar sua jornada.</p>}</div></section>

        <section className="border-b border-border"><div className="mx-auto grid max-w-7xl gap-8 px-4 py-14 sm:px-6 md:grid-cols-3">{[["01","Determinação","Você decide entrar no caminho."],["02","Disciplina","Você transforma intenção em prática."],["03","Direção","Você sabe qual é o próximo passo."]].map(([number,title,text]) => <div key={number} className="border-l-2 border-kaizen pl-5"><div className="font-mono text-xs text-kaizen">{number}</div><h3 className="mt-2 font-display text-xl font-bold">{title}</h3><p className="mt-1 text-sm text-muted-foreground">{text}</p></div>)}</div></section>
      </main>
    </div>
  );
}
