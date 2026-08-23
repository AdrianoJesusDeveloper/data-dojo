import { DojoHeader } from "@/components/DojoHeader";
import { AIChat } from "@/components/ai/AIChat";

export default function AiSales() {
  return (
    <div className="min-h-screen">
      <DojoHeader />
      <main className="max-w-7xl mx-auto px-6 py-10">
        <section className="mb-8">
          <h1 className="font-display text-4xl font-extrabold">💼 AI Sales</h1>
          <p className="text-muted-foreground mt-2">
            O agente comercial do Data Driven Dojô para orientar visitantes e futuros alunos.
          </p>
        </section>
        <AIChat mentor="ai_sales" />
      </main>
    </div>
  );
}
