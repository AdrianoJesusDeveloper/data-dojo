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
 export default function Workspace(){

const [course,setCourse]=useState<Course|null>(null);
const [currentLesson,setCurrentLesson]=useState<Lesson|null>(null);

const [loading,setLoading]=useState(true);

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



useEffect(()=>{

api
.get<PaginatedResponse<Course>|Course[]>("/api/courses/")

.then(response=>{

const data =
Array.isArray(response.data)
?
response.data
:
response.data.results;


if(data.length){

const active=data[0];

setCourse(active);


const lesson =
active.modules?.[0]?.lessons?.[0]
||
null;


setCurrentLesson(lesson);


if(lesson?.body){
setCode(lesson.body);
}

}


setLoading(false);

})

.catch(()=>{

toast.error(
"Falha ao conectar ao backend."
);

setLoading(false);

});


},[]);
const append=(line:string)=>{

setLines(previous=>[
...previous,
line
]);

};


const compileAndSubmit=async()=>{


if(!currentLesson?.exercise || running)
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



return (

<div className="min-h-screen flex flex-col">

<Toaster
position="top-right"
theme="dark"
/>


<DojoHeader/>


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



<button

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


</button>



<DojoTerminal

lines={lines}

/>


</section>


</main>


</div>


);


}
