import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AgentKey } from "./AIChat";

type Agent = { key: AgentKey; name: string; description: string; specialty: string; available: boolean; provider: string };

export function AISelector({ value, onChange }: { value: AgentKey; onChange: (agent: AgentKey) => void }){
const [agents, setAgents] = useState<Agent[]>([]);
const [error, setError] = useState("");

useEffect(() => {
  api.get<{ agents: Agent[] }>("/api/ai/agents/")
    .then(({ data }) => {
      setAgents(data.agents);
      if (!data.agents.some((agent) => agent.key === value && agent.available)) {
        const firstAvailable = data.agents.find((agent) => agent.available);
        if (firstAvailable) onChange(firstAvailable.key);
      }
    })
    .catch(() => setError("Não foi possível carregar os agentes."));
}, [onChange, value]);

return (

<div
className="
rounded-xl
border
bg-card
p-5
"
>

<h2 className="
font-bold
mb-4
">
Escolha seu Sensei IA
</h2>


<select
value={value}
onChange={(event) => onChange(event.target.value as AgentKey)}
className="
w-full
rounded-md
border
bg-background
p-2
"
>
{agents.map((agent) => <option key={agent.key} value={agent.key} disabled={!agent.available}>{agent.name}{agent.available ? "" : " (indisponível)"}</option>)}


</select>

{error && <p className="mt-3 text-sm text-destructive">{error}</p>}
{agents.length > 0 && <p className="mt-3 text-xs text-muted-foreground">{agents.find((agent) => agent.key === value)?.specialty}</p>}


</div>

)

}
