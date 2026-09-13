import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle, Play } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

type Unit = { id: number; title: string; objective: string; order: number; status: string };
type Journey = { id: number | null; formation: number; status: "NOT_STARTED" | "IN_PROGRESS" | "COMPLETED"; started_at: string | null; current_unit: Unit | null; last_position: Record<string, unknown> };

export function SenseiJourneyButton({ formationId, onOpen }: { formationId: number; onOpen: (unit: Unit | null) => void }) {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["sensei-study-journey", formationId], queryFn: async () => (await api.get<Journey>(`/api/library/sensei-formations/${formationId}/study-journey/`)).data, retry: false });
  const start = useMutation({ mutationFn: async () => (await api.post<Journey>(`/api/library/sensei-formations/${formationId}/study-journey/`, {})).data, onSuccess: (journey) => { queryClient.setQueryData(["sensei-study-journey", formationId], journey); onOpen(journey.current_unit); toast.success("Formação iniciada. Domínio permanece inalterado."); } });
  const journey = query.data;
  if (query.isLoading) return <Button className="mt-4" size="sm" variant="outline" disabled><LoaderCircle className="animate-spin" />Carregando jornada</Button>;
  if (!journey || journey.status === "NOT_STARTED") return <Button className="mt-4" size="sm" onClick={() => start.mutate()} disabled={start.isPending}><Play />INICIAR FORMAÇÃO</Button>;
  return <Button className="mt-4" size="sm" onClick={() => onOpen(journey.current_unit)}><Play />CONTINUAR FORMAÇÃO</Button>;
}
