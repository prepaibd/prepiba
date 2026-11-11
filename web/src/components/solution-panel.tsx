"use client";

import { useLang } from "@/hooks/use-lang";
import type { Reveal } from "@/lib/types";
import { MathText } from "./math-text";

export function SolutionPanel({ r }: { r: Reveal }) {
  const { lang } = useLang();
  const bn = lang === "bn";
  const s = r.solution;
  const pick = (en: string, b: string) => (bn && b ? b : en);

  return (
    <div className="space-y-3 text-sm">
      {r.source_defect && (
        <p className="rounded-lg bg-warn-soft px-3 py-2 text-warn">
          The printed question has an error, so it is not scored: {r.source_defect}
        </p>
      )}
      {r.answer_status === "disputed" && (
        <p className="rounded-lg bg-warn-soft px-3 py-2 text-warn">The answer key for this question is disputed.</p>
      )}
      {r.answer_text && <p><span className="font-medium">Answer:</span> <MathText text={r.answer_text} /></p>}
      {s && (
        <>
          <p><MathText text={pick(s.body_en, s.body_bn)} /></p>
          {(s.trap_en || s.trick_en) && (
            <ul className="space-y-1 text-muted">
              {s.trap_en && <li><b>Watch out:</b> <MathText text={pick(s.trap_en, s.trap_bn)} /></li>}
              {s.trick_en && <li><b>Shortcut:</b> <MathText text={pick(s.trick_en, s.trick_bn)} /></li>}
            </ul>
          )}
          {s.note && <p className="text-muted">{s.note}</p>}
          {[...s.formulas, ...s.rules].length > 0 && (
            <div className="space-y-2 border-t border-line pt-3">
              {[...s.formulas, ...s.rules].map((c) => (
                <details key={c.slug} className="rounded-lg bg-surface-2 px-3 py-2">
                  <summary className="cursor-pointer font-medium">{pick(c.title, c.title_bn)}</summary>
                  <p className="mt-1 text-muted"><MathText text={pick(c.body, c.body_bn)} /></p>
                </details>
              ))}
            </div>
          )}
        </>
      )}
      {r.review_note && <p className="text-xs text-muted">Note: {r.review_note}</p>}
    </div>
  );
}
