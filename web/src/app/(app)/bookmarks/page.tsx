"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { QuestionView } from "@/components/question-view";
import { SolutionPanel } from "@/components/solution-panel";
import { api, get } from "@/lib/api";
import type { Bookmark, Paginated, Reveal } from "@/lib/types";

function BookmarkCard({ b, onRemove }: { b: Bookmark; onRemove: () => void }) {
  const [reveal, setReveal] = useState<Reveal | null>(null);
  const [error, setError] = useState(false);

  async function show() {
    try { setReveal(await get<Reveal>(`/questions/${b.question.id}/solution/`)); }
    catch { setError(true); }
  }

  return (
    <article className="card space-y-4 p-5">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-muted">{b.question.exam.replace("iba_mba_", "").replace("_", " ")} · Q{b.question.number}</p>
        <div className="flex gap-2">
          <Link href={`/chat?q=${b.question.id}`} className="btn px-3 py-1 text-xs">Ask AI</Link>
          <button className="btn px-3 py-1 text-xs" onClick={onRemove}>Remove</button>
        </div>
      </div>
      <QuestionView q={b.question} correct={reveal ? reveal.correct_label : undefined} />
      {reveal ? <SolutionPanel r={reveal} /> : (
        <button className="btn" onClick={show}>Show answer &amp; solution</button>
      )}
      {error && <p role="alert" className="text-sm text-bad">Could not load the solution.</p>}
    </article>
  );
}

export default function Bookmarks() {
  const [items, setItems] = useState<Bookmark[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    get<Paginated<Bookmark>>("/bookmarks/", { page_size: 200 }).then((d) => setItems(d.results)).catch(() => setError(true));
  }, []);

  async function remove(b: Bookmark) {
    setItems((list) => list?.filter((x) => x.id !== b.id) ?? null);
    try { await api(`/bookmarks/${b.question.id}/`, { method: "DELETE" }); } catch { setItems((list) => (list ? [b, ...list] : [b])); }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="h1">Bookmarks</h1>
        <p className="text-muted">Questions you saved from your results.</p>
      </div>
      {error && <p role="alert" className="text-sm text-bad">Could not load bookmarks.</p>}
      {items === null && !error && <p className="text-sm text-muted">Loading…</p>}
      {items?.length === 0 && <p className="text-sm text-muted">Nothing saved yet. Bookmark questions while reviewing a result.</p>}
      {items?.map((b) => <BookmarkCard key={b.id} b={b} onRemove={() => remove(b)} />)}
    </div>
  );
}
