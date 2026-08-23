import { DojoHeader } from "@/components/DojoHeader";
import { AIChat } from "@/components/ai/AIChat";

const WHATSAPP_URL = "https://wa.me/5521972663791";

export default function AiSales() {
  return (
    <div className="min-h-screen">
      <DojoHeader />
      <main className="max-w-7xl mx-auto px-6 py-10">
        <section className="mb-8">
          <h1 className="font-display text-4xl font-extrabold">💼 AI Sales</h1>
          <p className="text-muted-foreground mt-2">
            Tire suas dúvidas sobre o Data Driven Dojô, cursos e trilhas diretamente com nosso agente comercial.
          </p>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <span className="text-sm text-muted-foreground">
              Não encontrou o que procura?
            </span>
            <a
              href={WHATSAPP_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center rounded-lg bg-green-600 px-5 py-2.5 font-semibold text-white transition hover:bg-green-700"
            >
              💬 Falar com um atendente no WhatsApp
            </a>
          </div>
        </section>
        <AIChat mentor="ai_sales" />
      </main>
    </div>
  );
}
