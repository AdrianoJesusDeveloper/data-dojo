import { BookOpen, ChevronDown, FileText, LoaderCircle, Printer, Save } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";

export type StudioSectionExportFormat = "pdf" | "docx" | "pptx";

type Props = {
  id: string;
  title: string;
  subtitle?: string;
  defaultOpen?: boolean;
  className?: string;
  children: ReactNode;
  onSave?: () => void;
  onExport?: (format: StudioSectionExportFormat) => void;
  exportingFormat?: StudioSectionExportFormat | null;
  saveDisabled?: boolean;
  exportDisabled?: boolean;
  actions?: ReactNode;
};

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function currentStylesheets() {
  const links = Array.from(document.querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"]'))
    .map((link) => {
      const href = link.getAttribute("href");
      if (!href) return "";
      const absoluteHref = new URL(href, window.location.href).href;
      return `<link rel="stylesheet" href="${escapeHtml(absoluteHref)}">`;
    })
    .filter(Boolean)
    .join("\n");

  const styles = Array.from(document.querySelectorAll<HTMLStyleElement>("style"))
    .map((style) => style.outerHTML)
    .join("\n");

  return `${links}\n${styles}`;
}

function printOnlySection(
  id: string,
  title: string,
  subtitle: string | undefined,
  printWindow: Window,
) {
  const source = document.getElementById(`${id}-content`);
  if (!source) {
    printWindow.document.write(`
      <!doctype html>
      <html lang="pt-BR">
        <head><meta charset="utf-8"><title>${escapeHtml(title)}</title></head>
        <body><p>Não foi possível preparar esta seção para impressão.</p></body>
      </html>
    `);
    printWindow.document.close();
    return;
  }

  const clone = source.cloneNode(true) as HTMLElement;

  clone
    .querySelectorAll(
      'button, input, textarea, select, [role="button"], .no-print, [data-print-exclude="true"]',
    )
    .forEach((element) => element.remove());

  clone.querySelectorAll("details").forEach((details) => {
    details.setAttribute("open", "");
  });

  clone.querySelectorAll<HTMLElement>("[hidden]").forEach((element) => {
    element.removeAttribute("hidden");
  });

  const subtitleHtml = subtitle
    ? `<p class="print-subtitle">${escapeHtml(subtitle)}</p>`
    : "";

  printWindow.document.open();
  printWindow.document.write(`<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>${escapeHtml(title)} — Data Driven Dojô</title>
  ${currentStylesheets()}
  <style>
    @page {
      size: A4;
      margin: 12mm;
    }

    html,
    body {
      margin: 0 !important;
      padding: 0 !important;
      width: auto !important;
      min-height: 0 !important;
      background: #ffffff !important;
      color: #111827 !important;
      overflow: visible !important;
      print-color-adjust: exact;
      -webkit-print-color-adjust: exact;
    }

    body {
      font-family: Arial, Helvetica, sans-serif !important;
      font-size: 10.5pt !important;
      line-height: 1.5 !important;
    }

    .print-page {
      width: 100% !important;
      max-width: 186mm !important;
      margin: 0 auto !important;
      padding: 0 !important;
      background: #ffffff !important;
      color: #111827 !important;
    }

    .print-header {
      margin: 0 0 8mm !important;
      padding: 0 0 5mm !important;
      border-bottom: 2px solid #0057b8 !important;
      break-after: avoid;
    }

    .print-brand {
      margin: 0 0 2mm !important;
      font-size: 8.5pt !important;
      font-weight: 700 !important;
      letter-spacing: .08em !important;
      text-transform: uppercase !important;
      color: #667085 !important;
    }

    .print-header h1 {
      margin: 0 !important;
      font-size: 21pt !important;
      line-height: 1.2 !important;
      color: #0057b8 !important;
    }

    .print-subtitle {
      margin: 2mm 0 0 !important;
      color: #475467 !important;
      font-size: 9.5pt !important;
    }

    .print-content,
    .print-content * {
      box-sizing: border-box !important;
      color: #111827 !important;
      text-shadow: none !important;
    }

    .print-content {
      position: static !important;
      inset: auto !important;
      width: auto !important;
      height: auto !important;
      max-height: none !important;
      overflow: visible !important;
      margin: 0 !important;
      padding: 0 !important;
      background: #ffffff !important;
      transform: none !important;
    }

    .print-content [class*="fixed"],
    .print-content [class*="sticky"] {
      position: static !important;
      inset: auto !important;
    }

    .print-content [class*="bg-"] {
      background: #ffffff !important;
    }

    .print-content [class*="text-muted"] {
      color: #667085 !important;
    }

    .print-content [class*="border"] {
      border-color: #d0d5dd !important;
    }

    .print-content [class*="shadow"] {
      box-shadow: none !important;
    }

    .print-content h1,
    .print-content h2,
    .print-content h3,
    .print-content h4 {
      break-after: avoid;
      page-break-after: avoid;
      color: #111827 !important;
    }

    .print-content p,
    .print-content li,
    .print-content td,
    .print-content th {
      orphans: 3;
      widows: 3;
    }

    .print-content article,
    .print-content section,
    .print-content table,
    .print-content pre,
    .print-content blockquote {
      max-width: 100% !important;
    }

    .print-content img,
    .print-content svg,
    .print-content canvas {
      max-width: 100% !important;
      height: auto !important;
    }

    .print-content pre,
    .print-content code {
      white-space: pre-wrap !important;
      overflow-wrap: anywhere !important;
    }

    .print-content a {
      color: #0057b8 !important;
      text-decoration: underline !important;
    }

    @media print {
      html,
      body,
      .print-page,
      .print-content {
        height: auto !important;
        min-height: 0 !important;
      }
    }
  </style>
</head>
<body>
  <main class="print-page">
    <header class="print-header">
      <p class="print-brand">DATA DRIVEN DOJÔ · CONTENT STUDIO</p>
      <h1>${escapeHtml(title)}</h1>
      ${subtitleHtml}
    </header>
    <div class="print-content">${clone.innerHTML}</div>
  </main>
</body>
</html>`);
  printWindow.document.close();
  printWindow.focus();

  printWindow.setTimeout(() => {
    printWindow.print();
  }, 350);
}

export function StudioSection({
  id,
  title,
  subtitle,
  defaultOpen = false,
  className = "",
  children,
  onSave,
  onExport,
  exportingFormat = null,
  saveDisabled = false,
  exportDisabled = false,
  actions,
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const [readingMode, setReadingMode] = useState(false);

  const sectionClass = useMemo(
    () =>
      readingMode
        ? "fixed inset-0 z-[100] overflow-y-auto bg-background p-4 sm:p-8"
        : `rounded-lg border p-4 ${className}`,
    [readingMode, className],
  );

  const handlePrint = () => {
    const printWindow = window.open("", "_blank", "width=1100,height=820");
    if (!printWindow) {
      window.alert(
        "O navegador bloqueou a janela de impressão. Permita pop-ups para localhost e tente novamente.",
      );
      return;
    }

    setOpen(true);
    window.setTimeout(() => {
      printOnlySection(id, title, subtitle, printWindow);
    }, 80);
  };

  return (
    <section data-studio-section={id} className={sectionClass}>
      <div className="no-print flex flex-wrap items-start justify-between gap-3">
        <button
          type="button"
          className="flex min-w-0 flex-1 items-start gap-2 text-left"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
          aria-controls={`${id}-content`}
        >
          <ChevronDown
            className={`mt-0.5 h-5 w-5 shrink-0 text-muted-foreground transition-transform ${
              open ? "rotate-180" : ""
            }`}
          />
          <span className="min-w-0">
            <span className="block font-bold">{title}</span>
            {subtitle && (
              <span className="mt-1 block text-xs text-muted-foreground">{subtitle}</span>
            )}
          </span>
        </button>

        <div
          className="flex flex-wrap items-center gap-1"
          role="group"
          aria-label={`Ações de ${title}`}
        >
          {onSave && (
            <Button size="sm" variant="ghost" disabled={saveDisabled} onClick={onSave}>
              <Save />
              Salvar
            </Button>
          )}

          <Button
            size="sm"
            variant={readingMode ? "default" : "ghost"}
            onClick={() => {
              setOpen(true);
              setReadingMode((value) => !value);
            }}
          >
            <BookOpen />
            {readingMode ? "Sair do modo leitura" : "Modo leitura"}
          </Button>

          <Button size="sm" variant="ghost" onClick={handlePrint}>
            <Printer />
            Imprimir
          </Button>

          {onExport && (
            <>
              <span className="mx-1 hidden h-6 w-px bg-border sm:block" aria-hidden="true" />
              {(["pdf", "docx", "pptx"] as const).map((format) => (
                <Button
                  key={format}
                  size="sm"
                  variant="ghost"
                  disabled={exportDisabled || exportingFormat !== null}
                  onClick={() => onExport(format)}
                >
                  {exportingFormat === format ? (
                    <LoaderCircle className="animate-spin" />
                  ) : (
                    <FileText />
                  )}
                  {format.toUpperCase()}
                </Button>
              ))}
            </>
          )}

          {actions}
        </div>
      </div>

      {open && (
        <div
          id={`${id}-content`}
          className={readingMode ? "mx-auto mt-6 max-w-5xl" : "mt-4"}
        >
          {children}
        </div>
      )}
    </section>
  );
}
