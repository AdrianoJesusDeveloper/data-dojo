import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiGet = vi.fn();
const apiPost = vi.fn();
const apiPatch = vi.fn();
vi.mock("@/lib/api", () => ({ api: { get: (...args: unknown[]) => apiGet(...args), post: (...args: unknown[]) => apiPost(...args), patch: (...args: unknown[]) => apiPatch(...args), delete: vi.fn() } }));
vi.mock("@/components/DojoHeader", () => ({ DojoHeader: () => <div>Header</div> }));
vi.mock("sonner", () => ({ Toaster: () => null, toast: { success: vi.fn(), error: vi.fn() } }));

import ProfessionalStudio, { ModalityPicker, ProposalExportPanel, type Modality } from "@/pages/ProfessionalStudio";

const catalog:Modality[]=[
 {id:1,name:"Desenvolvimento Web",slug:"web-development",domain:"SOFTWARE_DEVELOPMENT",domain_label:"Desenvolvimento de Software",is_active:true,sort_order:1},
 {id:2,name:"Inteligência Artificial",slug:"artificial-intelligence",domain:"AI_AUTOMATION",domain_label:"IA / Automação",is_active:true,sort_order:2},
];
const opportunity={id:10,title:"Projeto IA",description:"Briefing",source:"DIRECT_CLIENT",source_url:"",client_name:"",client_reference:"",budget_min:null,budget_max:null,currency:"BRL",deadline:null,proposal_deadline:null,status:"NEW",notes:"",modalities:catalog,created_at:"2026-08-30T12:00:00Z",updated_at:"2026-08-30T12:00:00Z"};

describe("Professional Studio modalities",()=>{
 beforeEach(()=>{vi.clearAllMocks();apiGet.mockImplementation((url:string)=>Promise.resolve(url.includes("modalities")?{data:catalog}:{data:{count:1,next:null,previous:null,results:[opportunity]}}));apiPost.mockResolvedValue({data:opportunity});apiPatch.mockResolvedValue({data:opportunity});});
 it("supports multiple selection and removal",()=>{const onChange=vi.fn();const {rerender}=render(<ModalityPicker catalog={catalog} selected={[]} onChange={onChange}/>);fireEvent.click(screen.getByRole("button",{name:"Desenvolvimento Web"}));expect(onChange).toHaveBeenCalledWith([1]);rerender(<ModalityPicker catalog={catalog} selected={[1,2]} onChange={onChange}/>);fireEvent.click(screen.getByRole("button",{name:/Desenvolvimento Web/}));expect(onChange).toHaveBeenLastCalledWith([2]);});
 it("loads catalog, renders chips, edits selections and sends modality_ids",async()=>{render(<ProfessionalStudio/>);expect(await screen.findByText("Projeto IA")).toBeTruthy();expect(screen.getAllByText("Desenvolvimento Web").length).toBeGreaterThan(0);fireEvent.click(screen.getByRole("button",{name:/Editar/}));const selected=await screen.findByRole("button",{name:/✓ Inteligência Artificial/});expect(selected.getAttribute("aria-pressed")).toBe("true");fireEvent.click(selected);fireEvent.click(screen.getByRole("button",{name:"Salvar oportunidade"}));await waitFor(()=>expect(apiPatch).toHaveBeenCalled());expect(apiPatch.mock.calls[0][1].modality_ids).toEqual([1]);});
 it("shows empty modality state",async()=>{apiGet.mockImplementation((url:string)=>Promise.resolve(url.includes("modalities")?{data:catalog}:{data:{count:1,next:null,previous:null,results:[{...opportunity,modalities:[]}]}}));render(<ProfessionalStudio/>);expect(await screen.findByText("Sem modalidades")).toBeTruthy();});
 it("handles catalog loading errors",async()=>{apiGet.mockImplementation((url:string)=>url.includes("modalities")?Promise.reject(new Error("network")):Promise.resolve({data:{count:0,next:null,previous:null,results:[]}}));render(<ProfessionalStudio/>);fireEvent.click(await screen.findByRole("button",{name:"Nova oportunidade"}));expect(await screen.findByText("Não foi possível carregar as modalidades.")).toBeTruthy();expect((screen.getByRole("button",{name:"Salvar oportunidade"}) as HTMLButtonElement).disabled).toBe(true);});
});

describe("Professional Studio proposal exports",()=>{
 const proposal={id:7,version:"CONSULTATIVE",status:"APPROVED",greeting:"Olá",understanding:"Necessidade",approach:"Abordagem",deliverables:["Painel"],deadline:"4 semanas",suggested_price:"1200.00",currency:"BRL",essential_questions:["Quem aprova?"],differentiators:["Validação"],closing:"Até breve"};
 beforeEach(()=>{vi.clearAllMocks();apiGet.mockResolvedValue({data:proposal});Object.defineProperty(URL,"createObjectURL",{configurable:true,value:vi.fn(()=>"blob:test")});Object.defineProperty(URL,"revokeObjectURL",{configurable:true,value:vi.fn()});vi.spyOn(HTMLAnchorElement.prototype,"click").mockImplementation(()=>{});});
 it("enables actions only after loading a persisted proposal",async()=>{render(<ProposalExportPanel opportunity={opportunity}/>);expect((screen.getByRole("button",{name:/Imprimir/}) as HTMLButtonElement).disabled).toBe(true);await waitFor(()=>expect((screen.getByRole("button",{name:/Exportar PDF/}) as HTMLButtonElement).disabled).toBe(false));expect(apiGet).toHaveBeenCalledWith("/api/professional/opportunities/10/proposal/",{params:{version:"CONSULTATIVE"}});});
 it("uses the selected version in PDF and DOCX export URLs",async()=>{render(<ProposalExportPanel opportunity={opportunity}/>);await waitFor(()=>expect((screen.getByRole("button",{name:/Exportar PDF/}) as HTMLButtonElement).disabled).toBe(false));fireEvent.change(screen.getByRole("combobox",{name:"Versão para exportação"}),{target:{value:"TECHNICAL"}});await waitFor(()=>expect(apiGet).toHaveBeenCalledWith("/api/professional/opportunities/10/proposal/",{params:{version:"TECHNICAL"}}));fireEvent.click(screen.getByRole("button",{name:/Exportar PDF/}));await waitFor(()=>expect(apiGet).toHaveBeenCalledWith("/api/professional/opportunities/10/proposal/export/pdf/",{params:{version:"TECHNICAL"},responseType:"blob"}));fireEvent.click(screen.getByRole("button",{name:/Exportar DOCX/}));await waitFor(()=>expect(apiGet).toHaveBeenCalledWith("/api/professional/opportunities/10/proposal/export/docx/",{params:{version:"TECHNICAL"},responseType:"blob"}));});
 it("keeps all actions disabled when no proposal is persisted",async()=>{apiGet.mockRejectedValue(new Error("not found"));render(<ProposalExportPanel opportunity={opportunity}/>);await waitFor(()=>expect(apiGet).toHaveBeenCalled());expect((screen.getByRole("button",{name:/Imprimir/}) as HTMLButtonElement).disabled).toBe(true);expect((screen.getByRole("button",{name:/Exportar PDF/}) as HTMLButtonElement).disabled).toBe(true);expect((screen.getByRole("button",{name:/Exportar DOCX/}) as HTMLButtonElement).disabled).toBe(true);});
});
