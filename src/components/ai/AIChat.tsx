import { FormEvent, useState } from "react";
import { api } from "@/lib/api";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export type AgentKey = "dojo_ai" | "sensei" | "data" | "ai_engineer" | "cloud" | "career" | "marketing" | "youtube" | "ai_sales";

const agentNames: Record<AgentKey, string> = {
  dojo_ai: "DDJ AI", sensei: "Sensei AI", data: "Data Sensei",
  ai_engineer: "AI Engineer Sensei", cloud: "Cloud Sensei",
  career: "Career Sensei", marketing: "Marketing Sensei",
  youtube: "YouTube Sensei", ai_sales: "AI Sales",
};

interface AIChatProps { mentor?: AgentKey; }

export function AIChat({ mentor = "dojo_ai" }: AIChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [message, setMessage] = useState("");
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const agentName = agentNames[mentor];

  async function sendMessage(event: FormEvent) {
    event.preventDefault();
    const text = message.trim();
    if (!text || loading) return;

    setError(null);
    setMessage("");
    setMessages((current) => [...current, { role: "user", content: text }]);
    setLoading(true);

    try {
      const response = await api.post("/api/ai/chat/", {
        mentor,
        message: text,
        conversation_id: conversationId,
      });

      setConversationId(response.data.conversation_id ?? conversationId);
      setMessages((current) => [
        ...current,
        { role: "assistant", content: response.data.message },
      ]);
    } catch (requestError: any) {
      const detail =
        requestError?.response?.data?.detail ||
        requestError?.response?.data?.error ||
        "Não foi possível conectar ao Sensei IA.";
      setError(detail);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl border bg-card overflow-hidden">
      <div className="border-b px-5 py-4">
        <h2 className="font-bold text-lg">
          🥋 {agentName}
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          {mentor === "ai_sales"
            ? "Converse com o agente comercial do Data Driven Dojô."
            : `Converse com o ${agentName} e receba uma orientação prática.`}
        </p>
      </div>

      <div className="min-h-[420px] max-h-[520px] overflow-y-auto p-5 space-y-4">
        {messages.length === 0 && (
          <div className="rounded-lg border border-dashed p-6 text-center text-muted-foreground">
            <p className="font-semibold text-foreground">O chat está pronto.</p>
            <p className="text-sm mt-2">
              {mentor === "ai_sales"
                ? "Pergunte sobre cursos, trilhas ou como começar no Dojô."
                : "Faça uma pergunta sobre Python, SQL, dados, IA, cloud ou sua jornada de aprendizado."}
            </p>
          </div>
        )}

        {messages.map((item, index) => (
          <div
            key={`${item.role}-${index}`}
            className={item.role === "user" ? "flex justify-end" : "flex justify-start"}
          >
            <div
              className={
                item.role === "user"
                  ? "max-w-[80%] rounded-xl px-4 py-3 bg-primary text-primary-foreground"
                  : "max-w-[80%] rounded-xl px-4 py-3 border bg-background"
              }
            >
              <p className="text-xs font-semibold mb-1 opacity-75">
                {item.role === "user" ? "Você" : agentName}
              </p>
              <p className="whitespace-pre-wrap text-sm leading-6">{item.content}</p>
            </div>
          </div>
        ))}

        {loading && (
          <div className="text-sm text-muted-foreground">O Sensei está pensando...</div>
        )}

        {error && (
          <div className="rounded-lg border border-destructive/30 p-3 text-sm text-destructive">
            {error}
          </div>
        )}
      </div>

      <form onSubmit={sendMessage} className="border-t p-4 flex gap-3">
        <input
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          disabled={loading}
          placeholder="Escreva sua pergunta..."
          className="flex-1 rounded-md border bg-background px-4 py-3 outline-none focus:ring-2 focus:ring-ring"
          aria-label="Mensagem para o agente de IA"
        />
        <button
          type="submit"
          disabled={loading || !message.trim()}
          className="rounded-md bg-primary px-5 py-3 text-primary-foreground font-semibold disabled:opacity-50"
        >
          {loading ? "..." : "Enviar"}
        </button>
      </form>
    </div>
  );
}
