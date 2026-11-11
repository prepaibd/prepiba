"use client";

import Link from "next/link";
import { useState } from "react";
import { get } from "@/lib/api";
import type { Question, Reveal } from "@/lib/types";
import { QuestionView } from "./question-view";
import { SolutionPanel } from "./solution-panel";

interface Props {
  q: Question;
  /** e.g. "Dec 2017" */
  session: string;
  saved: boolean;
  onToggleSave: () => void;
}

const label = (s: string) => s.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

/** One past-paper question in a read-only list: the question, a bookmark toggle, and an on-demand answer + solution. */
export function PastQuestion({ q, session, saved, onToggleSave }: Props) {
  const [reveal, setReveal] = useState<Reveal | null>(null);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);

  async function show() {
    setBusy(true);
    setError(false);
    try { setReveal(await get<Reveal>(`/questions/${q.id}/solution/`)); }
    catch { setError(true); }
    finally { setBusy(false); }
  }

  return (
    <article id={`q-${q.id}`} className="card space-y-4 p-5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="grid h-8 min-w-8 place-items-center rounded-full bg-surface-2 px-2 text-sm font-semibold tabular-nums">{q.number}</span>
        <p className="text-sm text-muted">{session}</p>
        {q.topic && <span className="chip">{q.topic.name}</span>}
        <span className="chip">{label(q.type)}</span>
        <div className="ml-auto flex gap-2">
          <Link href={`/chat?q=${q.id}`} className="btn px-3 py-1 text-xs">Ask AI</Link>
          <button className={`btn px-3 py-1 text-xs ${saved ? "border-accent bg-accent-soft text-accent" : ""}`}
            onClick={onToggleSave} aria-pressed={saved}>
            {saved ? "Saved" : "Save"}
          </button>
        </div>
      </div>
      <QuestionView q={q} showGroup={false} correct={reveal ? reveal.correct_label : undefined} />
      {reveal
        ? <SolutionPanel r={reveal} />
        : <button className="btn" onClick={show} disabled={busy}>{busy ? "Loading…" : "Show answer & solution"}</button>}
      {error && <p role="alert" className="text-sm text-bad">Could not load the solution.</p>}
    </article>
  );
}
