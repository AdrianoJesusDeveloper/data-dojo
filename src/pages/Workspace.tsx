import { api } from "@/lib/api";
import { createFileRoute } from "@tanstack/react-router";
import { DojoHeader } from "@/components/DojoHeader";

import { useEffect, useRef, useState } from "react";
import { toast, Toaster } from "sonner";

import { LessonPlayer } from "@/components/workspace/LessonPlayer";
import { CodeEditor } from "@/components/workspace/CodeEditor";
import { DojoTerminal } from "@/components/workspace/DojoTerminal";



interface Exercise {
  id:number;
  lesson:number;
  title:string;
  statement:string;
  answer_type:string;
  points:number;
  submission:{
    format:string;
    max_length:number;
    automated_evaluation:boolean;
  };
}

interface ExerciseAttempt {
  id:number;
  exercise:number;
  attempt_number:number;
  passed:boolean;
  feedback:{code:string;message:string};
  evaluation_version:string;
  created_at:string;
}


interface Lesson {
  id:number;
  title:string;
  content_type:string;
  file_upload:string|null;
  video_url:string|null;
  body:string;
  order:number;
  exercise:Exercise|null;
}


interface Module {
  id:number;
  title:string;
  order:number;
  lessons:Lesson[];
}


interface Course {
  id:number;
  title:string;
  description:string;
  modules:Module[];
}


interface PaginatedResponse<T>{
  count:number;
  next:string|null;
  previous:string|null;
  results:T[];
}

type CourseAccessType="enrollment"|"administrative"|"none";
interface CourseAccessResponse{
  access_type:CourseAccessType;
  courses:Course[];
}
interface CourseProgress{
  id:number;
  enrollment:number;
  course:Course;
  percentage:string;
  academic_state:"not_started"|"in_progress"|"completed";
  first_activity_at:string|null;
  last_activity_at:string|null;
  created_at:string;
  updated_at:string;
}
 export default function Workspace(){

const [course,setCourse]=useState<Course|null>(null);
const [availableCourses,setAvailableCourses]=useState<Course[]>([]);
const [currentLesson,setCurrentLesson]=useState<Lesson|null>(null);

const [loading,setLoading]=useState(true);
const [enrollingCourseId,setEnrollingCourseId]=useState<number|null>(null);
const [loadError,setLoadError]=useState(false);
const [accessType,setAccessType]=useState<CourseAccessType>("none");
const [progress,setProgress]=useState<CourseProgress|null>(null);
const [progressLoading,setProgressLoading]=useState(false);
const [progressError,setProgressError]=useState(false);

const [code,setCode]=useState("");

const [lines,setLines]=useState<string[]>([
 "$ dojo-cli pronto. Aguardando submissão..."
]);

const [running,setRunning]=useState(false);
const pendingSubmission=useRef<{
exerciseId:number;
answer:string;
key:string;
}|null>(null);



const selectCourse=(active:Course)=>{
setCourse(active);
const requestedLessonId=typeof window!=="undefined"?Number(new URLSearchParams(window.location.search).get("lesson")):0;
const requestedLesson=active.modules.flatMap((module)=>module.lessons).find((lesson)=>lesson.id===requestedLessonId);
const lesson=requestedLesson||active.modules?.[0]?.lessons?.[0]||null;
setCurrentLesson(lesson);
setCode(lesson?.content_type==="ARTICLE"?"":lesson?.body||"");
};

const loadProgress=async(active:Course)=>{
setProgressLoading(true);
setProgressError(false);
try{
const response=await api.get<CourseProgress>(`/api/course-progress/by-course/${active.id}/`);
if(typeof response.data?.percentage!=="string")throw new Error("Malformed course progress response");
setProgress(response.data);
}catch{
setProgress(null);
setProgressError(true);
}finally{
setProgressLoading(false);
}
};

const updateCoursePercentage=(percentage:string)=>{
setProgress((current)=>current?{...current,percentage}:current);
};

const loadWorkspace=async()=>{
setLoading(true);
setLoadError(false);
try{
const [catalogResponse,accessResponse]=await Promise.all([
api.get<PaginatedResponse<Course>|Course[]>("/api/courses/"),
api.get<CourseAccessResponse>("/api/enrollments/access/"),
]);
const catalog=Array.isArray(catalogResponse.data)?catalogResponse.data:catalogResponse.data.results;
const {access_type,courses}=accessResponse.data;
if(!["enrollment","administrative","none"].includes(access_type)||!Array.isArray(courses))throw new Error("Malformed course access response");
setAvailableCourses(catalog);
setAccessType(access_type);
if(courses.length){
const requestedCourseId=typeof window!=="undefined"?Number(new URLSearchParams(window.location.search).get("course")):0;
const selected=courses.find((item)=>item.id===requestedCourseId)||courses[0];
selectCourse(selected);
if(access_type==="enrollment")await loadProgress(selected);
}
}catch{
setLoadError(true);
toast.error("Falha ao carregar suas matrículas.");
}finally{
setLoading(false);
}
};

useEffect(()=>{void loadWorkspace();},[]);

const enroll=async(active:Course)=>{
if(enrollingCourseId!==null)return;
setEnrollingCourseId(active.id);
try{
await api.post("/api/enrollments/",{course_id:active.id});
selectCourse(active);
setAccessType("enrollment");
await loadProgress(active);
toast.success("Matrícula realizada.");
}catch{
toast.error("Não foi possível realizar a matrícula.");
}finally{
setEnrollingCourseId(null);
}
};
const append=(line:string)=>{

setLines(previous=>[
...previous,
line
]);

};


const compileAndSubmit=async()=>{


if(!currentLesson?.exercise || running || accessType!=="enrollment")
return;


setRunning(true);


append("$ dojo-cli submit desafio.sql");

const activeSubmission =
pendingSubmission.current?.exerciseId === currentLesson.exercise.id
&& pendingSubmission.current.answer === code
? pendingSubmission.current
: {
exerciseId:currentLesson.exercise.id,
answer:code,
key:crypto.randomUUID(),
};
pendingSubmission.current=activeSubmission;

try{
const response=await api.post<ExerciseAttempt>(
`/api/exercises/${activeSubmission.exerciseId}/attempts/`,
{
submitted_answer:activeSubmission.answer,
idempotency_key:activeSubmission.key,
}
);

const attempt=response.data;
if(
!attempt
|| typeof attempt.passed!=="boolean"
|| !attempt.feedback
|| typeof attempt.feedback.message!=="string"
){
throw new Error("Malformed exercise attempt response");
}

pendingSubmission.current=null;
append(`↳ Tentativa #${attempt.attempt_number} registrada.`);

if(attempt.passed){
append("✓ DESAFIO APROVADO");
toast.success(attempt.feedback.message);
}else{
append(`✗ ${attempt.feedback.message}`);
toast.error(attempt.feedback.message);
}
}catch{
append("✗ Não foi possível enviar a tentativa. Tente novamente.");
toast.error("Não foi possível enviar a tentativa. Tente novamente.");
}finally{
setRunning(false);
}


};
if(loading){

return (

<div className="min-h-screen bg-black flex items-center justify-center text-kaizen">

⏳ Carregando ecossistema do Dojô...

</div>

);

}

if(loadError){
return <div className="min-h-screen bg-black flex flex-col gap-4 items-center justify-center text-kaizen"><p>Não foi possível carregar o Workspace.</p><button className="rounded border border-kaizen px-4 py-2" onClick={()=>void loadWorkspace()}>Tentar novamente</button></div>;
}

if(!course){
return <div className="min-h-screen flex flex-col"><Toaster position="top-right" theme="dark"/><DojoHeader/><main className="mx-auto w-full max-w-4xl flex-1 px-4 py-10"><h1 className="font-display text-3xl font-bold">Escolha sua formação</h1><p className="mt-2 text-muted-foreground">Matricule-se para acessar o conteúdo no Workspace.</p>{availableCourses.length===0?<div className="mt-8 rounded-xl border border-border p-8 text-center text-muted-foreground">Nenhum curso disponível no momento.</div>:<div className="mt-8 grid gap-4 md:grid-cols-2">{availableCourses.map((available)=><article key={available.id} className="rounded-xl border border-border bg-card p-6"><h2 className="text-xl font-bold">{available.title}</h2><p className="mt-2 text-sm text-muted-foreground">{available.description}</p><button className="mt-5 rounded bg-kaizen px-4 py-2 font-bold text-kaizen-foreground disabled:opacity-60" disabled={enrollingCourseId!==null} onClick={()=>void enroll(available)}>{enrollingCourseId===available.id?"Matriculando...":"Matricular-se"}</button></article>)}</div>}</main></div>;
}



return (

<div className="min-h-screen flex flex-col">

<Toaster
position="top-right"
theme="dark"
/>


<DojoHeader/>

{accessType==="administrative"&&<div className="border-b border-kaizen/30 bg-kaizen/10 px-4 py-2 text-center text-sm font-medium text-kaizen">Acesso administrativo</div>}
{accessType==="enrollment"&&<div className="border-b border-border bg-card px-4 py-2 text-center text-sm text-muted-foreground">{progressLoading?"Carregando progresso...":progressError?"Progresso indisponível.":`Progresso: ${Number(progress?.percentage||0)}%${progress?.last_activity_at?` · Última atividade: ${new Date(progress.last_activity_at).toLocaleString("pt-BR")}`:""}`}</div>}


<main className="
flex-1
mx-auto
max-w-[1600px]
w-full
px-4
py-6
grid
lg:grid-cols-2
gap-4
">


<LessonPlayer

course={course}

currentLesson={currentLesson}

setCurrentLesson={setCurrentLesson}

setCode={setCode}

accessType={accessType}

onCourseProgressChange={updateCoursePercentage}

/>



<section className="
rounded-xl
border
border-border
bg-belt-black
overflow-hidden
flex
flex-col
">


<CodeEditor

code={code}

setCode={setCode}

/>



{accessType==="enrollment"?<button

onClick={compileAndSubmit}

disabled={running}

className="
m-3
rounded
bg-destructive
py-3
font-bold
"

>

{running
?
"Analisando..."
:
"⚔ Compilar desafio"
}


</button>:<div className="m-3 rounded border border-kaizen/30 bg-kaizen/10 px-4 py-3 text-center text-sm text-kaizen">Prévia administrativa: submissões acadêmicas desativadas.</div>}



<DojoTerminal

lines={lines}

/>


</section>


</main>


</div>


);


}
