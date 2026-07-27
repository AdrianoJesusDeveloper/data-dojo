interface DojoTerminalProps {
  lines: string[];
}

export function DojoTerminal({
  lines,
}: DojoTerminalProps) {
  return (
    <div className="bg-black border-t border-border overflow-hidden">
      <pre className="h-full p-4 font-mono text-xs text-[#9EE493] overflow-auto whitespace-pre-wrap">
        {lines.map((line, index) => (
          <div key={index}>
            {line || "\u00A0"}
          </div>
        ))}
      </pre>
    </div>
  );
}