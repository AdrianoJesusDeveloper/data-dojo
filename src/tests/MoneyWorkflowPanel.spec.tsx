import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { AxiosError } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks=vi.hoisted(()=>({get:vi.fn(),post:vi.fn(),patch:vi.fn()}));
const toastMocks=vi.hoisted(()=>({success:vi.fn(),error:vi.fn()}));
vi.mock("@/lib/api",()=>({api:apiMocks}));
vi.mock("sonner",()=>({toast:toastMocks}));

import { MoneyWorkflowPanel } from "../components/professional/MoneyWorkflowPanel";

const analysis={decision:"CAUTION",score:68,problem_summary:"Automatizar relatórios",client_need:"Reduzir trabalho manual",likely_deliverables:["Pipeline"],technical_risks:["API"],commercial_risks:["Escopo"],ambiguities:[],client_questions:["Qual o volume?"],competency_gap:{},score_breakdown:{},estimated_effort:{probable:"60h",suggested_deadline:"4 semanas"},pricing:{insufficient_data:false,suggested_range:"4–6 mil",minimum_recommended:"4 mil",target:"5,5 mil",justification:"Risco",change_factors:[]},limitations:["Revisão humana obrigatória"],ai_provider:"gemini",ai_model:"safe",generated_at:"2026-09-01"};
const proposal={id:1,version:"CONSULTATIVE",status:"DRAFT",greeting:"Olá!",understanding:"Automatizar relatórios",approach:"Construir pipeline",deliverables:["Pipeline"],deadline:"4 semanas",suggested_price:"5500.00",currency:"BRL",essential_questions:["Qual o volume?"],differentiators:["Validação incremental"],closing:"Vamos alinhar?",approved_at:null};
const plan={project:"Automação",phases:[{name:"Descoberta",acceptance_criteria:["Aprovado"],tasks:[{objective:"Validar dados",description:"Amostras",expected_result:"Mapa",validation:"Revisão",ai_help:"Documentação",human_validation:"Regras"}]}],risks:["Acesso"],validation:["Homologar"],delivery:["Código"],status:"DRAFT"};
function notFound(){const error=new AxiosError("not found");error.response={status:404} as never;return error;}

describe("PPS Money workflow",()=>{
 beforeEach(()=>{vi.resetAllMocks();vi.stubGlobal("navigator",{clipboard:{writeText:vi.fn().mockResolvedValue(undefined)}});apiMocks.get.mockRejectedValue(notFound());});
 it("analyzes pasted opportunity context and renders explainable viability",async()=>{
  let resolve!:(value:unknown)=>void;apiMocks.post.mockReturnValue(new Promise(done=>{resolve=done;}));
  render(<MoneyWorkflowPanel opportunityId={9}/>);
  fireEvent.click(screen.getByRole("button",{name:/Analisar oportunidade/}));
  expect(screen.getByRole("button",{name:/Analisar oportunidade/})).toBeDisabled();
  resolve({data:analysis});
  expect(await screen.findByText("CAUTION")).toBeInTheDocument();
  expect(screen.getByText("Score 68/100")).toBeInTheDocument();
  expect(screen.getByText("Revisão humana obrigatória")).toBeInTheDocument();
 });
 it("shows a non-sensitive generation error",async()=>{
  apiMocks.post.mockRejectedValue(new Error("provider secret"));render(<MoneyWorkflowPanel opportunityId={9}/>);
  fireEvent.click(screen.getByRole("button",{name:/Analisar oportunidade/}));
  expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível concluir a operação");
  expect(screen.getByRole("alert")).not.toHaveTextContent("provider secret");
 });
 it("generates, edits, approves, copies and creates the initial plan",async()=>{
  apiMocks.get.mockImplementation((url:string)=>url.endsWith("analysis/")?Promise.resolve({data:analysis}):Promise.reject(notFound()));
  apiMocks.post.mockImplementation((url:string)=>{
   if(url.endsWith("generate-proposal/"))return Promise.resolve({data:proposal});
   if(url.endsWith("proposal/approve/"))return Promise.resolve({data:{...proposal,status:"APPROVED",approved_at:"2026-09-01"}});
   if(url.endsWith("generate-execution-plan/"))return Promise.resolve({data:plan});
   return Promise.resolve({data:analysis});
  });
  apiMocks.patch.mockResolvedValue({data:{...proposal,understanding:"Entendimento revisado"}});
  render(<MoneyWorkflowPanel opportunityId={9}/>);
  await screen.findByText("Score 68/100");
  fireEvent.click(screen.getByRole("button",{name:/Gerar proposta/}));
  const understanding=await screen.findByLabelText("Entendimento");
  fireEvent.change(understanding,{target:{value:"Entendimento revisado"}});
  fireEvent.click(screen.getByRole("button",{name:"Salvar edição"}));
  await waitFor(()=>expect(apiMocks.patch).toHaveBeenCalledWith(expect.stringContaining("/proposal/"),expect.objectContaining({understanding:"Entendimento revisado",version:"CONSULTATIVE"})));
  fireEvent.click(screen.getByRole("button",{name:/Aprovar proposta/}));
  expect(await screen.findByText("APPROVED")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button",{name:/Copiar proposta/}));
  await waitFor(()=>expect(navigator.clipboard.writeText).toHaveBeenCalledWith(expect.stringContaining("Automatizar relatórios")));
  fireEvent.click(screen.getByRole("button",{name:/Gerar plano inicial/}));
  expect(await screen.findByText("Automação")).toBeInTheDocument();
  expect(screen.getByText(/Validar dados/)).toBeInTheDocument();
 });
});
