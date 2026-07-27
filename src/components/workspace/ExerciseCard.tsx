interface Exercise {
  title: string;
  answer_type: string;
  statement: string;
  expected_keywords: string[];
}

interface ExerciseCardProps {
  exercise: Exercise;
}

export function ExerciseCard({ exercise }: ExerciseCardProps) {
  return (
    <div className="mt-4 rounded-lg border border-border bg-background/70 p-4">
      <div className="text-xs font-bold uppercase tracking-[0.2em] text-kaizen">
        Exercício · {exercise.answer_type}
      </div>

      <div className="mt-2 text-sm font-semibold">
        {exercise.title}
      </div>

      <div className="mt-2 text-sm text-muted-foreground whitespace-pre-wrap">
        {exercise.statement}
      </div>

      {exercise.expected_keywords.length > 0 && (
        <div className="mt-3 text-xs text-muted-foreground">
          Critérios: {exercise.expected_keywords.join(", ")}
        </div>
      )}
    </div>
  );
}