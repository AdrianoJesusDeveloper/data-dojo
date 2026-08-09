import { DojoHeader } from "@/components/DojoHeader";
import { AIChat } from "@/components/ai/AIChat";
import { AISelector } from "@/components/ai/AISelector";
import { AIMentorCard } from "@/components/ai/AIMentorCard";


export default function Ai(){

return (

<div className="min-h-screen">

<DojoHeader/>


<main className="
max-w-7xl
mx-auto
px-6
py-10
">


<section className="mb-8">

<h1 className="
font-display
text-4xl
font-extrabold
">

🤖 DDJ AI

</h1>


<p className="
text-muted-foreground
mt-2
">

Seu conselho de inteligência artificial para evolução no caminho dos dados.

</p>


</section>



<div className="
grid
lg:grid-cols-4
gap-6
">


<aside className="
lg:col-span-1
space-y-4
">


<AIMentorCard/>


<AISelector/>


</aside>



<section className="
lg:col-span-3
">


<AIChat/>


</section>



</div>



</main>


</div>

)

}