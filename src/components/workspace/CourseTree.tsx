interface Lesson {
  id:number;
  title:string;
  content_type:string;
  body?:string;
}

interface Module {
  id:number;
  title:string;
  lessons:Lesson[];
}

interface Course {
  modules?:Module[];
}

interface CourseTreeProps {
  course:Course | null;
  currentLesson:Lesson | null;
  setCurrentLesson:(lesson:Lesson)=>void;
  setCode:(value:string)=>void;
}


export function CourseTree({
  course,
  currentLesson,
  setCurrentLesson,
  setCode,
}:CourseTreeProps){

return (
<div className="mt-6 border-t border-border pt-4">

<div className="font-display font-semibold text-sm mb-3">
🗂 Estrutura do Curso
</div>


{course?.modules?.map((module)=>(
<div key={module.id} className="mb-4">

<div className="text-xs font-bold text-kaizen uppercase mb-1">
{module.title}
</div>


<div className="space-y-1">

{module.lessons.map((lesson)=>(
<button
key={lesson.id}
onClick={()=>{
setCurrentLesson(lesson);
if(lesson.body){
setCode(lesson.body);
}
}}
className={`w-full text-left text-sm px-3 py-2 rounded transition ${
currentLesson?.id===lesson.id
?
"bg-destructive text-destructive-foreground font-semibold"
:
"bg-background hover:bg-muted text-muted-foreground"
}`}
>

{lesson.content_type==="VIDEO"?"▶ ":"📄 "}
{lesson.title}

</button>
))}

</div>
</div>
))}

</div>
)

}