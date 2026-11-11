/** Splitting text into plain and math segments. Pure functions, no React or KaTeX. */
export type Seg = { kind: "text" | "inline" | "display"; value: string };

const isSpace = (c: string | undefined) => c === undefined || /\s/.test(c);
const isDigit = (c: string | undefined) => c !== undefined && c >= "0" && c <= "9";

/**
 * Index of the next unescaped `delim` at or after `from`, or -1.
 * `strict` is for AI output, where `$` is often currency. It applies the TeX-in-markdown rule (the closing `$`
 * must touch non-space text and not be followed by a digit) and rejects a span that contains another stray `$`,
 * so "from $40 to $50" stays prose. Question data is validated by tools/validate.py and parsed leniently: strict
 * mode would reject some of it, e.g. the span `$\$$306`.
 */
function findClose(src: string, from: number, delim: string, strict: boolean): number {
  for (let j = from; j < src.length; j++) {
    if (src.startsWith(delim, j)) {
      if (!strict || delim !== "$") return j;
      if (!isSpace(src[j - 1]) && !isDigit(src[j + 1])) return j;
      return -1; // a stray dollar inside the span: it was currency, so the opening `$` was literal text
    }
    if (src[j] === "\\") j++; // skip an escaped character such as \$
  }
  return -1;
}

/** Split text into plain and math segments. `\$` is a literal dollar; `$..$`, `$$..$$` and `\(..\)` are math. */
export function parseMath(src: string, strict = false): Seg[] {
  const segs: Seg[] = [];
  let buf = "";
  const flush = () => { if (buf) { segs.push({ kind: "text", value: buf }); buf = ""; } };
  let i = 0;
  while (i < src.length) {
    const c = src[i];
    if (c === "\\" && src[i + 1] === "$") { buf += "$"; i += 2; continue; }
    let open = "", close = "", kind: Seg["kind"] = "inline";
    if (c === "$") {
      if (src[i + 1] === "$") { open = "$$"; close = "$$"; kind = "display"; }
      else if (!(strict && isSpace(src[i + 1]))) { open = "$"; close = "$"; }
    } else if (c === "\\" && src[i + 1] === "(") { open = "\\("; close = "\\)"; }
    if (open) {
      const end = findClose(src, i + open.length, close, strict);
      if (end > i + open.length) {
        flush();
        segs.push({ kind, value: src.slice(i + open.length, end) });
        i = end + close.length;
        continue;
      }
    }
    buf += c;
    i++;
  }
  flush();
  return segs;
}


export interface Run extends Seg { bold: boolean }

/**
 * Apply `**bold**` across segments. A bold span may contain math ("**Step 1: solve $x$.**"), so the on/off
 * state is carried across segments rather than reset for each text piece.
 */
export function markBold(segs: Seg[]): Run[] {
  const out: Run[] = [];
  let bold = false;
  for (const seg of segs) {
    if (seg.kind !== "text") { out.push({ ...seg, bold }); continue; }
    seg.value.split("**").forEach((piece, k) => {
      if (k > 0) bold = !bold;
      if (piece) out.push({ kind: "text", value: piece, bold });
    });
  }
  return out;
}
