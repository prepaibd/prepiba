"use client";

import { useLang } from "@/hooks/use-lang";
import type { Group, Question } from "@/lib/types";
import { MathText } from "./math-text";

interface Props {
  /** Render the shared instruction/passage/table. Lists turn this off and render <GroupContext> once per group. */
  showGroup?: boolean;
  q: Question;
  selected?: string | null;
  onSelect?: (label: string) => void;
  /** Review mode: mark the right and wrong options. */
  correct?: string | null;
}

export function QuestionView({ q, selected, onSelect, correct, showGroup = true }: Props) {
  const { lang } = useLang();
  const bn = lang === "bn";
  const stem = bn && q.stem_bn ? q.stem_bn : q.stem;
  const reviewing = correct !== undefined;

  return (
    <div className="space-y-4">
      {showGroup && <GroupContext g={q.group} />}
      {bn && q.stem_bn && q.bn_status === "draft" && (
        <span className="chip" title="Bangla translation has not been reviewed yet">Bangla: draft translation</span>
      )}
      <p className="text-base"><MathText text={stem} /></p>
      {q.figures.map((f) => (
        // eslint-disable-next-line @next/next/no-img-element
        <img key={f.url} src={f.url} alt={f.caption || "Figure"} className="max-h-72 rounded-lg border border-line bg-white" />
      ))}
      <ul className="space-y-2" role={onSelect ? "radiogroup" : "list"}>
        {q.options.map((o) => {
          const picked = selected === o.label;
          const isRight = reviewing && correct === o.label;
          const isWrong = reviewing && picked && correct !== o.label;
          const tone = isRight ? "border-ok bg-ok-soft" : isWrong ? "border-bad bg-bad-soft"
            : picked ? "border-accent bg-accent-soft" : "border-line hover:bg-surface-2";
          const body = (
            <>
              <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full border border-current text-xs font-semibold">
                {o.label}
              </span>
              <span className="text-left text-sm"><MathText text={bn && o.text_bn ? o.text_bn : o.text} /></span>
              {isRight && <span className="ml-auto text-xs font-medium text-ok">Correct</span>}
              {isWrong && <span className="ml-auto text-xs font-medium text-bad">Your answer</span>}
            </>
          );
          return (
            <li key={o.label}>
              {onSelect ? (
                <button type="button" role="radio" aria-checked={picked} onClick={() => onSelect(o.label)}
                  className={`flex w-full items-center gap-3 rounded-lg border px-3 py-2.5 ${tone}`}>
                  {body}
                </button>
              ) : (
                <div className={`flex items-center gap-3 rounded-lg border px-3 py-2.5 ${tone}`}>{body}</div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/** The instruction, passage and table shared by a group of questions. */
export function GroupContext({ g }: { g: Group | null }) {
  const { lang } = useLang();
  if (!g) return null;
  const bn = lang === "bn";
  const instruction = bn && g.instruction_bn ? g.instruction_bn : g.instruction;
  const passage = bn && g.passage_bn ? g.passage_bn : g.passage;
  return (
    <div className="space-y-4">
    {instruction && (
      <p className="rounded-lg bg-surface-2 px-3 py-2 text-sm text-muted"><MathText text={instruction} /></p>
    )}
    {passage && (
      <div className="max-h-80 overflow-y-auto rounded-lg border border-line px-3 py-2 text-sm">
        <MathText text={passage} />
      </div>
    )}
    {g?.table && (
      <div className="overflow-x-auto">
        <table className="text-sm">
          <tbody>
            {g.table.rows.map((row, r) => (
              <tr key={r}>{row.map((cell, c) => <td key={c} className="border border-line px-2 py-1">{cell}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
    </div>
  );
}

/** True when `q` starts a new group (or has none) relative to the question listed before it. */
export const startsGroup = (q: Question, prev?: Question) => !!q.group && q.group.id !== prev?.group?.id;
