import { Link, createFileRoute } from "@tanstack/react-router";
import { ArrowLeft, LockKeyhole, ShoppingBag } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

export const Route = createFileRoute("/store/checkout")({ component: StoreCheckoutPage });

type CartItem = { id: string; title: string; price: number; quantity: number };

function readCart(): CartItem[] {
  if (typeof window === "undefined") return [];
  try { return JSON.parse(localStorage.getItem("ddj-store-cart") || "[]"); } catch { return []; }
}

export function StoreCheckoutPage() {
  const [cart, setCart] = useState<CartItem[]>([]);
  useEffect(() => setCart(readCart()), []);
  const total = useMemo(() => cart.reduce((sum, item) => sum + item.price * item.quantity, 0), [cart]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border bg-background/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
          <Link to="/store" className="flex items-center gap-2 text-sm font-semibold hover:text-kaizen"><ArrowLeft className="h-4 w-4" /> Voltar à 3DStore</Link>
          <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-muted-foreground"><LockKeyhole className="h-4 w-4" /> Checkout 3DStore</div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:py-16">
        <div className="grid gap-8 lg:grid-cols-[1fr_380px]">
          <section className="rounded-2xl border border-border bg-card p-6 sm:p-8">
            <div className="flex items-center gap-3"><ShoppingBag className="h-6 w-6 text-kaizen" /><div><p className="font-mono text-xs uppercase tracking-wider text-kaizen">Finalização</p><h1 className="font-display text-3xl font-bold">Seu pedido</h1></div></div>
            {cart.length === 0 ? <div className="py-16 text-center"><p className="text-muted-foreground">Seu carrinho está vazio.</p><Link to="/store" className="mt-5 inline-flex rounded-xl bg-kaizen px-5 py-3 font-display font-bold text-kaizen-foreground">Explorar produtos</Link></div> : <div className="mt-8 space-y-4">{cart.map(item => <div key={item.id} className="flex justify-between border-b border-border pb-4"><div><p className="font-display font-bold">{item.title}</p><p className="text-sm text-muted-foreground">Qtd. {item.quantity}</p></div><strong>R$ {(item.price * item.quantity).toFixed(2).replace('.', ',')}</strong></div>)}</div>}
            {cart.length > 0 && <div className="mt-8 grid gap-4 sm:grid-cols-2"><label className="text-sm font-medium">Nome<input className="mt-2 w-full rounded-xl border border-border bg-background px-4 py-3" placeholder="Seu nome" /></label><label className="text-sm font-medium">E-mail<input type="email" className="mt-2 w-full rounded-xl border border-border bg-background px-4 py-3" placeholder="voce@email.com" /></label></div>}
          </section>
          <aside className="h-fit rounded-2xl border border-border bg-card p-6"><p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Resumo</p><div className="mt-4 flex justify-between text-lg font-bold"><span>Total</span><span className="text-kaizen">R$ {total.toFixed(2).replace('.', ',')}</span></div><button disabled={cart.length === 0} className="mt-6 w-full rounded-xl bg-kaizen px-5 py-4 font-display font-bold text-kaizen-foreground disabled:cursor-not-allowed disabled:opacity-40">Continuar para pagamento</button><p className="mt-3 text-center text-xs leading-5 text-muted-foreground">Pagamento online será conectado na próxima etapa. Nenhuma cobrança é realizada nesta versão.</p></aside>
        </div>
      </main>
    </div>
  );
}
