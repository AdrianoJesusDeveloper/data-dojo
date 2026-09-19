import type { ReadingMark } from "./library-api";

function rangeFromOffsets(container: HTMLElement, start: number, end: number) {
  if (start < 0 || end <= start) return null;
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  let node: Node | null;
  let offset = 0;
  let started = false;
  const range = document.createRange();

  while ((node = walker.nextNode())) {
    const length = node.textContent?.length ?? 0;
    if (!started && start <= offset + length) {
      range.setStart(node, Math.max(0, start - offset));
      started = true;
    }
    if (started && end <= offset + length) {
      range.setEnd(node, Math.max(0, end - offset));
      return range;
    }
    offset += length;
  }
  return null;
}

export function selectedRange(container: HTMLElement | null) {
  const selection = window.getSelection();
  if (!container || !selection?.rangeCount || selection.isCollapsed) return null;
  const range = selection.getRangeAt(0);
  if (!container.contains(range.startContainer) || !container.contains(range.endContainer)) return null;
  const before = range.cloneRange(); before.selectNodeContents(container); before.setEnd(range.startContainer, range.startOffset);
  const start = before.toString().length;
  return { selected_text: range.toString(), start_offset: start, end_offset: start + range.toString().length };
}

export function restoreHighlights(container: HTMLElement | null, marks: ReadingMark[]) {
  const css = CSS as typeof CSS & { highlights?: Map<string, unknown> };
  const HighlightClass = (window as unknown as { Highlight?: new (...ranges: Range[]) => unknown }).Highlight;
  if (!css.highlights || !HighlightClass || !container) return;
  const ranges: Range[] = [];
  for (const mark of marks.filter(m => m.kind === "highlight")) {
    if (mark.start_offset === null || mark.end_offset === null) continue;
    const range = rangeFromOffsets(container, mark.start_offset, mark.end_offset);
    if (range && range.toString() === mark.selected_text) ranges.push(range);
  }
  css.highlights.set("dojo-reader", new HighlightClass(...ranges));
}

export function setNarratorHighlight(container: HTMLElement | null, start: number, end: number) {
  const css = CSS as typeof CSS & { highlights?: Map<string, unknown> };
  const HighlightClass = (window as unknown as { Highlight?: new (...ranges: Range[]) => unknown }).Highlight;
  if (!css.highlights || !HighlightClass || !container) return;
  const range = rangeFromOffsets(container, start, end);
  if (!range) return;
  css.highlights.set("dojo-narrator", new HighlightClass(range));
}

export function clearNarratorHighlight() {
  const css = CSS as typeof CSS & { highlights?: Map<string, unknown> };
  css.highlights?.delete("dojo-narrator");
}
