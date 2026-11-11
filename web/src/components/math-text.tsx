import katex from "katex";
import { Fragment } from "react";
import { markBold, parseMath } from "@/lib/math-parse";

function render(tex: string, displayMode: boolean) {
  return katex.renderToString(tex, { displayMode, throwOnError: false, strict: "ignore", output: "htmlAndMathml" });
}

/** `*italic*` and `code` within one text piece. Returns React nodes, never raw HTML, so model output cannot inject markup. */
function inline(text: string) {
  return text.split(/(\*[^*\s][^*\n]*\*|`[^`\n]+`)/g).map((p, i) => {
    if (p.length > 2 && p.startsWith("*") && p.endsWith("*")) return <em key={i}>{p.slice(1, -1)}</em>;
    if (p.length > 2 && p.startsWith("`") && p.endsWith("`"))
      return <code key={i} className="rounded bg-surface-2 px-1 text-[0.9em]">{p.slice(1, -1)}</code>;
    return <Fragment key={i}>{p}</Fragment>;
  });
}

const lite = (t: string) =>
  t.replace(/^\s*-{3,}\s*$/gm, "")
    .replace(/^(\s*)[-*]\s+/gm, "$1• ")
    .replace(/^(\s*•\s+)?#{1,6}\s+/gm, "$1"); // headings, also when the model puts one after a bullet

interface Props {
  text: string;
  className?: string;
  /** Render **bold**, *italic*, `code` and bullet lists (for AI replies). Implies `strict`. */
  markdown?: boolean;
  /** Treat `$` as currency unless it clearly delimits a formula. Use for free text typed by people or models. */
  strict?: boolean;
}

export function MathText({ text, className = "", markdown = false, strict = markdown }: Props) {
  const segs = parseMath(text, strict);
  const runs = markdown ? markBold(segs) : segs.map((s) => ({ ...s, bold: false }));
  return (
    <span className={`whitespace-pre-wrap ${className}`}>
      {runs.map((r, i) => {
        const node = r.kind === "text" ? (
          <Fragment>{markdown ? inline(lite(r.value)) : r.value}</Fragment>
        ) : (
          <span className={r.kind === "display" ? "block my-2 overflow-x-auto" : undefined}
            dangerouslySetInnerHTML={{ __html: render(r.value, r.kind === "display") }} />
        );
        return r.bold ? <strong key={i}>{node}</strong> : <Fragment key={i}>{node}</Fragment>;
      })}
    </span>
  );
}
