import { useEffect } from "react";
import { useParams, useSearch } from "@tanstack/react-router";
import { Toaster } from "sonner";
import { DojoHeader } from "@/components/DojoHeader";
import { IntelligentBriefingPanel } from "@/components/professional/IntelligentBriefingPanel";
export default function ProfessionalBriefing(){const {opportunityId}=useParams({strict:false}) as {opportunityId:string};const search=useSearch({strict:false}) as {print?:string|number};useEffect(()=>{if(String(search.print)==="1")setTimeout(()=>window.print(),300)},[search.print]);return <div className="min-h-screen bg-background text-foreground"><div className="no-print"><DojoHeader/></div><Toaster position="top-right" richColors/><main className="mx-auto max-w-5xl px-4 py-8 sm:py-12"><IntelligentBriefingPanel opportunityId={Number(opportunityId)} standalone/></main></div>}
