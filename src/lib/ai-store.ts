interface AIState {

selectedMentor:string;

history:[
 {
  role:"user"|"assistant",
  message:string
 }
]

}