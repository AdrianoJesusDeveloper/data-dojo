import { describe, expect, it } from "vitest";
import { downloadFilename } from "@/lib/download-filename";

describe("downloadFilename", () => {
  it("decodes UTF-8 and removes path separators and control characters", () => {
    expect(downloadFilename("attachment; filename*=UTF-8''forma%C3%A7%C3%A3o%2Fplano%00.docx", "fallback.docx")).toBe("formação_plano_.docx");
    expect(downloadFilename('attachment; filename="..\\plano.docx"', "fallback")).toBe(".._plano.docx");
  });
  it("preserves a safe fallback for malformed encoding", () => {
    expect(downloadFilename("attachment; filename*=UTF-8''%ZZ; filename=plano.pdf", "fallback")).toBe("plano.pdf");
    expect(downloadFilename(undefined, "plano.pdf")).toBe("plano.pdf");
  });
});
