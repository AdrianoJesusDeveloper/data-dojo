interface AIMentor {
  name: string;
  role: string;
  icon: string;
  description: string;
}

const mentor: AIMentor = {
  name: "Sensei Código",
  role: "Copilot",
  icon: "💻",
  description:
    "Especialista em programação, arquitetura e boas práticas.",
};

export function AIMentorCard() {
  return (
    <div className="rounded-xl border bg-card p-5">
      <div className="text-5xl mb-3">{mentor.icon}</div>

      <h2 className="text-xl font-bold">
        {mentor.name}
      </h2>

      <p className="text-sm text-muted-foreground mb-3">
        {mentor.role}
      </p>

      <p className="text-sm">
        {mentor.description}
      </p>
    </div>
  );
}