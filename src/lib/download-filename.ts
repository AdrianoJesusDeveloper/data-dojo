export function downloadFilename(disposition: string | undefined, fallback: string) {
  const encoded = disposition?.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  const plain = disposition?.match(/filename=(?:"([^"]+)"|([^;]+))/i);
  let name = plain?.[1] || plain?.[2]?.trim() || fallback;
  if (encoded) {
    try { name = decodeURIComponent(encoded); } catch { /* Use the plain filename. */ }
  }
  return Array.from(name, (character) =>
    character.charCodeAt(0) < 32 || character === "/" || character === "\\" ? "_" : character,
  ).join("");
}
