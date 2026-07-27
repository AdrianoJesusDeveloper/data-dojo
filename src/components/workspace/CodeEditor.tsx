interface CodeEditorProps {
  code: string;
  setCode: (value: string) => void;
}

export function CodeEditor({
  code,
  setCode,
}: CodeEditorProps) {
  return (
    <div className="relative flex overflow-hidden">
      <div className="select-none font-mono text-xs leading-relaxed text-muted-foreground/50 py-4 pl-3 pr-2 text-right border-r border-border/40 bg-black/40">
        {code.split("\n").map((_, index) => (
          <div key={index}>
            {index + 1}
          </div>
        ))}
      </div>

      <textarea
        spellCheck={false}
        value={code}
        onChange={(event) => setCode(event.target.value)}
        className="flex-1 bg-belt-black text-belt-white font-mono text-sm p-4 resize-none outline-none leading-relaxed"
      />
    </div>
  );
}