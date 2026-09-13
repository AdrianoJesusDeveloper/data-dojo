import { createFileRoute } from "@tanstack/react-router";
import ProfessionalBriefing from "@/pages/ProfessionalBriefing";
export const Route=createFileRoute("/professional-studio/opportunities/$opportunityId/briefing")({component:ProfessionalBriefing});
