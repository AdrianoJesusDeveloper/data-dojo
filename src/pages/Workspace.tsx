import { api } from "@/lib/api";
import { createFileRoute } from "@tanstack/react-router";
import { DojoHeader } from "@/components/DojoHeader";
import { useDojo, useHydrated } from "@/lib/dojo-store";
import {
  celebratePromotion,
  celebrateXp,
} from "@/lib/celebrate";

import { useEffect, useState } from "react";
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
  expected_answer:string;
  expected_keywords:string[];
  evaluation_mode:string;
  points:number;
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

const {state, submitChallenge}=useDojo();
const hydrated=useHydrated();


const [course,setCourse]=useState<Course|null>(null);
const [currentLesson,setCurrentLesson]=useState<Lesson|null>(null);

const [loading,setLoading]=useState(true);

const [code,setCode]=useState("");

const [lines,setLines]=useState<string[]>([
 "$ dojo-cli pronto. Aguardando submissão..."
]);

const [running,setRunning]=useState(false);



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


if(!currentLesson)
return;


setRunning(true);


append(
"$ dojo-cli submit desafio.sql"
);


await new Promise(
r=>setTimeout(r,500)
);



const points=
currentLesson.exercise?.points ?? 120;



const result =
submitChallenge(
currentLesson.title,
points,
1.5
);



append(
`✓ DESAFIO APROVADO +${points} XP`
);



if(result.promoted){

celebratePromotion(
result.newBelt.color
);

toast.success(
`🥋 PROMOVIDO ${result.newBelt.name}`
);


}else{


celebrateXp();

toast.success(
`+${points} XP`
);

}


setRunning(false);


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