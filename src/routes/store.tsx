import { Link, createFileRoute, useNavigate } from "@tanstack/react-router";
import { ExternalLink, HelpCircle, MessageCircle, Minus, Plus, Search, ShoppingBag, Star, Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { toast, Toaster } from "sonner";
import logoDojo from "../assets/logo_transparente.png";
import { API_ORIGIN, api, getAuthToken } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";

export const Route = createFileRoute("/store")({ component: StorePage });

type Product = { id: number; name: string; short_description: string; price: string; image_url?: string; stock: number; product_type: "digital" | "physical" | "service"; sales_model: "own" | "affiliate" | "dropship"; category?: { name: string; slug: string }; rating_average: number | null; reviews_count: number; questions_count: number; partner_name?: string | null; affiliate_disclosure?: string | null; fulfillment_details?: { handling_days: number; shipping_origin: string } | null };
type CartItem = { id: number; product: Product; quantity: number; subtotal: string };
type Cart = { id: number; items: CartItem[]; total: string };
type Order = { id: number; status: string; total: string; created_at: string };
type Question = { id: number; username: string; question: string; answer: string; created_at: string; is_owner: boolean };
type Review = { id: number; username: string; rating: number; comment: string; verified_purchase: boolean; created_at: string; is_owner: boolean };
type ProductDiscussion = { questions: Question[]; reviews: Review[]; loading: boolean };
type Category = { id: number; name: string; slug: string; description: string };
type Paginated<T> = { count: number; next: string | null; previous: string | null; results: T[] };

const money = (value: string | number) => new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value));
const list = <T,>(data: T[] | { results: T[] }): T[] => Array.isArray(data) ? data : data.results || [];

function StorePage() {
  const navigate = useNavigate();
  const [products, setProducts] = useState<Product[]>([]);
  const [cart, setCart] = useState<Cart | null>(null);
  const [storedOrders, setOrders] = useState<Order[]>([]);
  const orders = storedOrders.filter((order) => order.status !== "cancelled");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<number | "checkout" | null>(null);
  const [quantities, setQuantities] = useState<Record<number, number>>({});
  const [expanded, setExpanded] = useState<number | null>(null);
  const [discussions, setDiscussions] = useState<Record<number, ProductDiscussion>>({});
  const [questionDrafts, setQuestionDrafts] = useState<Record<number, string>>({});
  const [reviewDrafts, setReviewDrafts] = useState<Record<number, string>>({});
  const [ratings, setRatings] = useState<Record<number, number>>({});
  const [authenticated, setAuthenticated] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [salesFilter, setSalesFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [catalogCount, setCatalogCount] = useState(0);
  const [hasNextPage, setHasNextPage] = useState(false);
  const [hasPreviousPage, setHasPreviousPage] = useState(false);
  const filteredProducts = products;

  const filtersActive = Boolean(search || categoryFilter !== "all" || typeFilter !== "all" || salesFilter !== "all");

  function clearFilters() {
    setSearch("");
    setCategoryFilter("all");
    setTypeFilter("all");
    setSalesFilter("all");
    setPage(1);
  }

  function logout() {
    useAuthStore.getState().logout();
    localStorage.removeItem("token");
    localStorage.removeItem("profile_preview");
    toast.success("Você saiu da 3DStore.");
    navigate({ to: "/login", search: { redirect: "/store" } });
  }

  useEffect(() => { (async () => {
    const hasSession = !!getAuthToken();
    setAuthenticated(hasSession);
    try {
      const { data: categoryData } = await api.get<Category[] | Paginated<Category>>("/api/store/categories/");
      setCategories(list(categoryData));
      if (hasSession) {
        const [cartResponse, ordersResponse] = await Promise.all([api.get<Cart>("/api/store/cart/"), api.get<Order[] | { results: Order[] }>("/api/store/orders/")]);
        setCart(cartResponse.data);
        setOrders(list(ordersResponse.data).filter((order) => order.status !== "cancelled"));
      }
    } catch { toast.error("Não foi possível carregar a 3DStore."); }
    finally { /* O carregamento do catálogo é controlado separadamente. */ }
  })(); }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => { setPage(1); }, [debouncedSearch, categoryFilter, typeFilter, salesFilter]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    api.get<Product[] | Paginated<Product>>("/api/store/products/", {
      signal: controller.signal,
      params: {
        page,
        ...(debouncedSearch ? { search: debouncedSearch } : {}),
        ...(categoryFilter !== "all" ? { category: categoryFilter } : {}),
        ...(typeFilter !== "all" ? { product_type: typeFilter } : {}),
        ...(salesFilter !== "all" ? { sales_model: salesFilter } : {}),
      },
    }).then(({ data }) => {
      const catalog = list(data);
      setProducts(catalog);
      setCatalogCount(Array.isArray(data) ? data.length : data.count);
      setHasNextPage(!Array.isArray(data) && Boolean(data.next));
      setHasPreviousPage(!Array.isArray(data) && Boolean(data.previous));
      setQuantities((current) => ({ ...current, ...Object.fromEntries(catalog.map((product) => [product.id, current[product.id] || 1])) }));
    }).catch((error) => {
      if (error?.code !== "ERR_CANCELED") toast.error("Não foi possível carregar o catálogo.");
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [page, debouncedSearch, categoryFilter, typeFilter, salesFilter]);

  const maxQuantity = (product: Product) => product.product_type === "physical" ? product.stock : 99;
  const changeSelectedQuantity = (product: Product, value: number) => setQuantities((current) => ({ ...current, [product.id]: Math.min(Math.max(value, 1), Math.max(maxQuantity(product), 1)) }));

  async function add(product: Product) {
    if (!authenticated) { navigate({ to: "/login", search: { redirect: "/store" } }); return; }
    const quantity = quantities[product.id] || 1;
    setBusy(product.id);
    try {
      setCart((await api.post<Cart>("/api/store/cart/items/", { product_id: product.id, quantity })).data);
      toast.success(`${quantity} × ${product.name} adicionado ao carrinho.`);
    } catch (error: any) { toast.error(error?.response?.data?.detail || "Não foi possível adicionar o produto."); }
    finally { setBusy(null); }
  }

  function visitPartner(product: Product) {
    window.open(
      `${API_ORIGIN}/api/store/products/${product.id}/affiliate/redirect/?campaign=3dstore_catalog`,
      "_blank",
      "noopener,noreferrer",
    );
  }

  async function update(item: CartItem, quantity: number) {
    setBusy(item.product.id);
    try {
      if (quantity < 1) await remove(item);
      else setCart((await api.patch<Cart>(`/api/store/cart/items/${item.id}/`, { quantity })).data);
    } catch (error: any) { toast.error(error?.response?.data?.detail || "Não foi possível atualizar o carrinho."); }
    finally { setBusy(null); }
  }

  async function remove(item: CartItem) {
    setBusy(item.product.id);
    try {
      const response = await api.delete<Cart>(`/api/store/cart/items/${item.id}/`);
      setCart(response.data?.items ? response.data : (await api.get<Cart>("/api/store/cart/")).data);
      toast.success(`${item.product.name} removido do carrinho.`);
    } catch (error: any) { toast.error(error?.response?.data?.detail || "Não foi possível remover o item do carrinho."); }
    finally { setBusy(null); }
  }

  async function toggleDiscussion(productId: number) {
    if (expanded === productId) { setExpanded(null); return; }
    setExpanded(productId);
    if (discussions[productId]) return;
    setDiscussions((current) => ({ ...current, [productId]: { questions: [], reviews: [], loading: true } }));
    try {
      const [questions, reviews] = await Promise.all([
        api.get<Question[] | { results: Question[] }>(`/api/store/products/${productId}/questions/`),
        api.get<Review[] | { results: Review[] }>(`/api/store/products/${productId}/reviews/`),
      ]);
      const reviewList = list(reviews.data);
      const ownReview = reviewList.find((review) => review.is_owner);
      if (ownReview) { setRatings((current) => ({ ...current, [productId]: ownReview.rating })); setReviewDrafts((current) => ({ ...current, [productId]: ownReview.comment })); }
      setDiscussions((current) => ({ ...current, [productId]: { questions: list(questions.data), reviews: reviewList, loading: false } }));
    } catch { toast.error("Não foi possível carregar perguntas e avaliações."); setDiscussions((current) => ({ ...current, [productId]: { questions: [], reviews: [], loading: false } })); }
  }

  async function ask(productId: number) {
    const question = questionDrafts[productId]?.trim();
    if (!authenticated) { navigate({ to: "/login", search: { redirect: "/store" } }); return; }
    if (!question) return;
    try {
      const { data } = await api.post<Question>(`/api/store/products/${productId}/questions/`, { question });
      setDiscussions((current) => ({ ...current, [productId]: { ...current[productId], questions: [data, ...current[productId].questions] } }));
      setQuestionDrafts((current) => ({ ...current, [productId]: "" }));
      setProducts((current) => current.map((product) => product.id === productId ? { ...product, questions_count: product.questions_count + 1 } : product));
      toast.success("Pergunta enviada.");
    } catch (error: any) { toast.error(error?.response?.data?.detail || "Não foi possível enviar a pergunta."); }
  }

  async function review(productId: number) {
    const comment = reviewDrafts[productId]?.trim();
    const rating = ratings[productId] || 0;
    if (!authenticated) { navigate({ to: "/login", search: { redirect: "/store" } }); return; }
    if (!comment || rating < 1) { toast.error("Informe uma nota e escreva sua avaliação."); return; }
    try {
      const existing = discussions[productId]?.reviews.find((item) => item.is_owner);
      const { data } = existing
        ? await api.patch<Review>(`/api/store/reviews/${existing.id}/`, { rating, comment })
        : await api.post<Review>(`/api/store/products/${productId}/reviews/`, { rating, comment });
      const reviews = existing ? discussions[productId].reviews.map((item) => item.id === data.id ? data : item) : [data, ...discussions[productId].reviews];
      setDiscussions((current) => ({ ...current, [productId]: { ...current[productId], reviews } }));
      const average = reviews.reduce((sum, item) => sum + item.rating, 0) / reviews.length;
      setProducts((current) => current.map((product) => product.id === productId ? { ...product, reviews_count: reviews.length, rating_average: Number(average.toFixed(1)) } : product));
      toast.success(existing ? "Avaliação atualizada." : "Avaliação publicada.");
    } catch (error: any) { toast.error(error?.response?.data?.non_field_errors?.[0] || "Não foi possível publicar a avaliação."); }
  }

  async function checkout() {
    setBusy("checkout");
    try {
      const { data } = await api.post<Order>("/api/store/checkout/", { provider: "mercado_pago" });
      setCart((current) => current ? { ...current, items: [], total: "0.00" } : current);
      setOrders((current) => [data, ...current]);
      toast.success(`Pedido #${data.id} criado com sucesso.`);
    } catch (error: any) { toast.error(error?.response?.data?.detail || "Não foi possível concluir o pedido."); }
    finally { setBusy(null); }
  }

  async function cancelPurchase() {
    if (!window.confirm("Deseja remover todos os itens e cancelar esta compra?")) return;
    setBusy("checkout");
    try {
      setCart((await api.delete<Cart>("/api/store/cart/")).data);
      toast.success("Compra cancelada e carrinho esvaziado.");
    } catch (error: any) { toast.error(error?.response?.data?.detail || "Não foi possível cancelar a compra."); }
    finally { setBusy(null); }
  }

  async function cancelOrder(order: Order) {
    if (!window.confirm(`Deseja cancelar o pedido #${order.id}?`)) return;
    setBusy("checkout");
    try {
      const { data } = await api.post<Order>(`/api/store/orders/${order.id}/cancel/`);
      setOrders((current) => current.filter((item) => item.id !== data.id));
      setCart((current) => current ? { ...current, items: [], total: "0.00" } : current);
      const { data: catalogData } = await api.get<Product[] | { results: Product[] }>("/api/store/products/");
      setProducts(list(catalogData));
      toast.success(`Pedido #${order.id} cancelado.`);
    } catch (error: any) { toast.error(error?.response?.data?.detail || "Não foi possível cancelar o pedido."); }
    finally { setBusy(null); }
  }

  return <div className="min-h-screen bg-background text-foreground"><Toaster position="top-right" theme="dark" richColors />
    <header className="sticky top-0 z-20 border-b border-border bg-background/90 backdrop-blur"><div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6"><Link to="/" className="flex min-w-0 items-center gap-3"><img src={logoDojo} alt="Data Driven Dojô Store" className="h-10 w-10 shrink-0 object-contain" /><div className="min-w-0"><div className="truncate font-display text-lg font-bold">Data Driven Dojô Store</div><div className="hidden font-mono text-[10px] uppercase tracking-[.22em] text-muted-foreground sm:block">3DStore · Loja oficial do Dojô</div></div></Link><div className="flex shrink-0 items-center gap-2"><Link to="/" className="rounded-lg border border-border px-3 py-2 text-sm hover:bg-secondary sm:px-4">Voltar ao Dojô</Link>{authenticated && <button type="button" onClick={logout} className="rounded-lg border border-destructive/60 px-3 py-2 text-sm font-bold text-destructive hover:bg-destructive/10 sm:px-4">Sair</button>}</div></div></header>
    <main className="mx-auto max-w-7xl px-4 py-12 sm:px-6"><div className="mb-10"><div className="inline-flex items-center gap-2 text-kaizen"><ShoppingBag className="h-5 w-5" /> Arsenal Kaizen</div><h1 className="mt-3 font-display text-4xl font-extrabold sm:text-6xl">Recursos para sua evolução.</h1><p className="mt-4 max-w-2xl text-muted-foreground">Produtos e materiais conectados diretamente ao catálogo do Dojô.</p></div>
      <div className="grid gap-8 lg:grid-cols-[1fr_360px]"><section><div className="mb-5 flex items-center justify-between gap-3"><h2 className="font-display text-2xl font-bold">Catálogo</h2>{filtersActive && <button type="button" onClick={clearFilters} className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-kaizen"><X size={15} /> Limpar filtros</button>}</div><div className="mb-6 rounded-2xl border border-border bg-card p-4"><label className="relative block"><Search className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" /><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar produtos, serviços ou parceiros" className="w-full rounded-xl border border-border bg-background py-3 pl-11 pr-4 text-sm outline-none transition focus:border-kaizen" /></label><div className="mt-3 grid gap-3 sm:grid-cols-3"><select aria-label="Filtrar por categoria" value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)} className="rounded-xl border border-border bg-background px-3 py-2 text-sm"><option value="all">Todas as categorias</option>{categories.map((category) => <option key={category.slug} value={category.slug}>{category.name}</option>)}</select><select aria-label="Filtrar por tipo" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)} className="rounded-xl border border-border bg-background px-3 py-2 text-sm"><option value="all">Produtos e serviços</option><option value="digital">Produtos digitais</option><option value="physical">Produtos físicos</option><option value="service">Serviços</option></select><select aria-label="Filtrar por origem" value={salesFilter} onChange={(event) => setSalesFilter(event.target.value)} className="rounded-xl border border-border bg-background px-3 py-2 text-sm"><option value="all">Todas as ofertas</option><option value="own">Ofertas da 3DStore</option><option value="affiliate">Produtos afiliados</option><option value="dropship">Dropshipping</option></select></div><p className="mt-3 text-xs text-muted-foreground">{catalogCount} {catalogCount === 1 ? "resultado encontrado" : "resultados encontrados"}</p></div>{loading ? <p className="text-muted-foreground">Carregando produtos...</p> : filteredProducts.length === 0 ? <div className="rounded-xl border border-border bg-card p-8 text-muted-foreground">{filtersActive ? "Nenhum produto ou serviço corresponde aos filtros." : "Nenhum produto disponível no momento."}</div> : <div className="grid gap-5 md:grid-cols-2">{filteredProducts.map((product) => <article key={product.id} className="h-fit rounded-2xl border border-border bg-card p-6">{product.image_url && <img src={product.image_url} alt="" loading="lazy" decoding="async" className="mb-5 h-40 w-full rounded-xl object-cover" />}<p className="font-mono text-xs uppercase tracking-wider text-kaizen">{product.category?.name || product.product_type}</p><h3 className="mt-2 font-display text-2xl font-bold">{product.name}</h3><p className="mt-3 min-h-12 text-sm text-muted-foreground">{product.short_description}</p>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-sm"><span className={product.product_type === "physical" && product.stock < 5 ? "text-orange-400" : "text-muted-foreground"}>{product.sales_model === "affiliate" ? `Vendido por ${product.partner_name || "parceiro"}` : product.product_type === "physical" ? (product.stock > 0 ? `${product.stock} unidade${product.stock === 1 ? "" : "s"} em estoque` : "Produto esgotado") : "Disponível"}</span><span className="inline-flex items-center gap-1 text-kaizen"><Star size={14} fill="currentColor" /> {product.rating_average ?? "Novo"} ({product.reviews_count})</span></div>
        {product.sales_model === "affiliate" ? <><div className="mt-5 flex flex-wrap items-center justify-between gap-3"><strong className="text-xl">{money(product.price)}</strong><button onClick={() => visitPartner(product)} className="inline-flex items-center gap-2 rounded-xl bg-kaizen px-4 py-2 font-bold text-kaizen-foreground">Comprar no parceiro <ExternalLink size={16} /></button></div><p className="mt-3 rounded-lg border border-kaizen/30 bg-kaizen/5 p-3 text-xs text-muted-foreground">{product.affiliate_disclosure}</p></> : <><div className="mt-5 flex flex-wrap items-center justify-between gap-3"><strong className="text-xl">{money(product.price)}</strong><div className="flex items-center gap-2"><div className="flex items-center rounded-lg border border-border"><button aria-label="Diminuir quantidade selecionada" onClick={() => changeSelectedQuantity(product, (quantities[product.id] || 1) - 1)} disabled={(quantities[product.id] || 1) <= 1} className="p-2 disabled:opacity-30"><Minus size={14} /></button><span className="min-w-8 text-center font-semibold">{quantities[product.id] || 1}</span><button aria-label="Aumentar quantidade selecionada" onClick={() => changeSelectedQuantity(product, (quantities[product.id] || 1) + 1)} disabled={(quantities[product.id] || 1) >= maxQuantity(product)} className="p-2 disabled:opacity-30"><Plus size={14} /></button></div><button onClick={() => add(product)} disabled={busy === product.id || (product.product_type === "physical" && product.stock < 1)} className="rounded-xl bg-kaizen px-4 py-2 font-bold text-kaizen-foreground disabled:opacity-50">{busy === product.id ? "Adicionando..." : "Adicionar"}</button></div></div>{product.sales_model === "dropship" && <p className="mt-3 text-xs text-muted-foreground">Enviado por {product.partner_name || "fornecedor parceiro"}{product.fulfillment_details?.shipping_origin ? ` de ${product.fulfillment_details.shipping_origin}` : ""}. Preparação em até {product.fulfillment_details?.handling_days || 2} dias úteis.</p>}</>}
        <button onClick={() => toggleDiscussion(product.id)} className="mt-5 flex w-full items-center justify-center gap-3 border-t border-border pt-4 text-sm text-muted-foreground hover:text-kaizen"><MessageCircle size={16} /> {product.questions_count} perguntas · {product.reviews_count} avaliações</button>
        {expanded === product.id && <div className="mt-5 space-y-6 border-t border-border pt-5">{discussions[product.id]?.loading ? <p className="text-sm text-muted-foreground">Carregando...</p> : <><div><h4 className="flex items-center gap-2 font-display font-bold"><HelpCircle size={17} /> Perguntas</h4><div className="mt-3 flex gap-2"><input value={questionDrafts[product.id] || ""} onChange={(event) => setQuestionDrafts((current) => ({ ...current, [product.id]: event.target.value }))} placeholder={authenticated ? "Faça uma pergunta sobre o produto" : "Entre para fazer uma pergunta"} className="min-w-0 flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm" /><button onClick={() => ask(product.id)} className="rounded-lg border border-kaizen px-3 text-sm font-bold text-kaizen">Enviar</button></div><div className="mt-4 space-y-3">{!discussions[product.id]?.questions.length ? <p className="text-sm text-muted-foreground">Seja o primeiro a perguntar.</p> : discussions[product.id].questions.map((item) => <div key={item.id} className="rounded-lg bg-background/60 p-3 text-sm"><strong>{item.username}</strong><p className="my-1">{item.question}</p>{item.answer && <div className="mt-2 border-l-2 border-kaizen pl-3 text-muted-foreground"><strong className="text-kaizen">Resposta da loja</strong><p className="my-1">{item.answer}</p></div>}</div>)}</div></div>
          <div><h4 className="flex items-center gap-2 font-display font-bold"><Star size={17} /> Avaliações</h4><div className="mt-3 flex gap-1">{[1,2,3,4,5].map((value) => <button key={value} aria-label={`${value} estrelas`} onClick={() => setRatings((current) => ({ ...current, [product.id]: value }))} className={(ratings[product.id] || 0) >= value ? "text-kaizen" : "text-muted-foreground"}><Star size={20} fill={(ratings[product.id] || 0) >= value ? "currentColor" : "none"} /></button>)}</div><textarea value={reviewDrafts[product.id] || ""} onChange={(event) => setReviewDrafts((current) => ({ ...current, [product.id]: event.target.value }))} placeholder={authenticated ? "Conte como foi sua experiência" : "Entre para avaliar"} rows={3} className="mt-2 w-full rounded-lg border border-border bg-background p-3 text-sm" /><button onClick={() => review(product.id)} className="mt-2 rounded-lg border border-kaizen px-3 py-2 text-sm font-bold text-kaizen">Publicar avaliação</button><div className="mt-4 space-y-3">{!discussions[product.id]?.reviews.length ? <p className="text-sm text-muted-foreground">Este produto ainda não possui avaliações.</p> : discussions[product.id].reviews.map((item) => <div key={item.id} className="rounded-lg bg-background/60 p-3 text-sm"><div className="flex items-center justify-between gap-2"><strong>{item.username} {item.verified_purchase && <span className="ml-1 text-xs font-normal text-green-400">Compra verificada</span>}</strong><span className="text-kaizen">{"★".repeat(item.rating)}</span></div><p className="mb-0 mt-1 text-muted-foreground">{item.comment}</p></div>)}</div></div></>}</div>}
      </article>)}</div>}{!loading && (hasPreviousPage || hasNextPage) && <div className="mt-6 flex items-center justify-center gap-3"><button type="button" onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={!hasPreviousPage} className="rounded-lg border border-border px-4 py-2 text-sm disabled:opacity-40">Anterior</button><span className="text-sm text-muted-foreground">Página {page}</span><button type="button" onClick={() => setPage((current) => current + 1)} disabled={!hasNextPage} className="rounded-lg border border-border px-4 py-2 text-sm disabled:opacity-40">Próxima</button></div>}</section>
        <aside className="h-fit rounded-2xl border border-border bg-card p-6 lg:sticky lg:top-24"><h2 className="font-display text-2xl font-bold">Carrinho</h2>{!authenticated ? <div className="mt-5"><p className="text-sm text-muted-foreground">Entre na sua conta para comprar, perguntar e avaliar produtos.</p><div className="mt-4 grid gap-2"><Link to="/login" search={{ redirect: "/store" }} className="inline-flex justify-center rounded-xl bg-kaizen px-4 py-2 font-bold text-kaizen-foreground">Entrar</Link><Link to="/register" className="inline-flex justify-center rounded-xl border border-kaizen px-4 py-2 font-bold text-kaizen">Criar conta</Link><Link to="/recuperar-senha" className="mt-1 text-center text-sm text-muted-foreground underline-offset-4 hover:text-kaizen hover:underline">Esqueci minha senha</Link></div></div> : !cart?.items.length ? <p className="mt-5 text-sm text-muted-foreground">Seu carrinho está vazio.</p> : <><div className="mt-5 space-y-4">{cart.items.map((item) => <div key={item.id} className="border-b border-border pb-4"><div className="flex items-start justify-between gap-3"><div className="font-semibold">{item.product.name}</div><button aria-label={`Remover ${item.product.name} do carrinho`} title="Remover do carrinho" onClick={() => remove(item)} disabled={busy === item.product.id} className="rounded p-1 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive disabled:opacity-50"><Trash2 size={16} /></button></div><div className="mt-2 flex items-center justify-between"><div className="flex items-center gap-2"><button aria-label="Diminuir quantidade" onClick={() => update(item, item.quantity - 1)} disabled={busy === item.product.id} className="rounded border border-border p-1 disabled:opacity-50">{item.quantity === 1 ? <Trash2 size={14} /> : <Minus size={14} />}</button><span>{item.quantity}</span><button aria-label="Aumentar quantidade" onClick={() => update(item, item.quantity + 1)} disabled={busy === item.product.id || (item.product.product_type === "physical" && item.quantity >= item.product.stock)} className="rounded border border-border p-1 disabled:opacity-50"><Plus size={14} /></button></div><strong>{money(item.subtotal)}</strong></div></div>)}</div><div className="mt-5 flex justify-between text-lg"><span>Total</span><strong>{money(cart.total)}</strong></div><button onClick={checkout} disabled={busy === "checkout"} className="mt-5 w-full rounded-xl bg-kaizen px-4 py-3 font-bold text-kaizen-foreground disabled:opacity-50">{busy === "checkout" ? "Processando..." : "Finalizar pedido"}</button><button onClick={cancelPurchase} disabled={busy === "checkout"} className="mt-2 w-full rounded-xl border border-destructive/60 px-4 py-2 text-sm font-bold text-destructive hover:bg-destructive/10 disabled:opacity-50">Cancelar compra</button><p className="mt-3 text-xs text-muted-foreground">O pedido será criado com pagamento pendente.</p></>}{authenticated && orders.length > 0 && <div className="mt-7 border-t border-border pt-5"><h3 className="font-display font-bold">Pedidos recentes</h3><div className="mt-3 space-y-3">{orders.slice(0, 5).map((order) => <div key={order.id} className="rounded-lg border border-border p-3 text-sm"><div className="flex items-center justify-between"><span>#{order.id} · {order.status}</span><strong>{money(order.total)}</strong></div>{order.status === "pending" && <button onClick={() => cancelOrder(order)} disabled={busy === "checkout"} className="mt-2 text-xs font-bold text-destructive hover:underline disabled:opacity-50">Cancelar pedido</button>}</div>)}</div></div>}</aside>
      </div></main>
  </div>;
}
