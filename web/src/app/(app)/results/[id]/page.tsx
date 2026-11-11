"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { QuestionView } from "@/components/question-view";
import { SolutionPanel } from "@/components/solution-panel";
import { useBookmarks } from "@/hooks/use-bookmarks";
import { ApiError, get } from "@/lib/api";
import type { AttemptResult, Breakdown, ReviewItem } from "@/lib/types";

type Filter = "all" | "wrong" | "unanswered" | "flagged";
const SUBJECT: Record<string, string> = {
  language: "Language & Communication", mathematics: "Mathematics", analytical: "Analytical Ability", writing: "Writing",
};

function Bars({ rows, title }: { rows: Breakdown[]; title: string }) {
  return (
    <section className="card space-y-3 p-5">
      <h2 className="h2">{title}</h2>
      {rows.map((r) => (
        <div key={String(r.id)} className="space-y-1">
          <div className="flex justify-between gap-3 text-sm">
            <span className="truncate">{SUBJECT[r.label] ?? r.label}</span>
            <span className="shrink-0 tabular-nums text-muted">{r.correct}/{r.total} correct · {Math.round(r.accuracy * 100)}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-surface-2" role="img" aria-label={`${Math.round(r.accuracy * 100)}% correct`}>
            <div className="h-full rounded-full bg-accent" style={{ width: `${Math.round(r.accuracy * 100)}%` }} />
          </div>
        </div>
      ))}
    </section>
  );
}

export default function Results() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [data, setData] = useState<AttemptResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const { ids, toggle } = useBookmarks();

  useEffect(() => {
    get<AttemptResult>(`/attempts/${id}/result/`)
      .then(setData)
      .catch((e) => {
        if (e instanceof ApiError && e.status === 409) router.replace(`/attempt/${id}`);
        else setError("Could not load the results.");
      });
  }, [id, router]);

  const shown = useMemo<ReviewItem[]>(() => {
    if (!data) return [];
    return data.review.filter((r) =>
      filter === "all" ? true
        : filter === "wrong" ? r.is_correct === false
        : filter === "unanswered" ? r.response.selected === null
        : r.response.flagged);
  }, [data, filter]);

  if (error) return <p role="alert" className="text-bad">{error}</p>;
  if (!data) return <p className="text-sm text-muted">Loading…</p>;

  const answered = (data.correct ?? 0) + (data.wrong ?? 0);
  const weakest = [...data.by_topic].filter((t) => t.total >= 2).sort((a, b) => a.accuracy - b.accuracy).slice(0, 5);

  return (
    <div className="space-y-6">
      <div>
        <Link href="/dashboard" className="text-sm text-muted hover:text-ink">← Dashboard</Link>
        <h1 className="h1 mt-1">{data.exam ? data.exam.session : "Practice"} results</h1>
        {data.status === "expired" && <p className="text-sm text-warn">Time ran out, so the attempt was submitted automatically.</p>}
      </div>

      <div className="card grid gap-4 p-5 sm:grid-cols-4">
        <div className="sm:col-span-1">
          <p className="text-sm text-muted">Score</p>
          <p className="text-3xl font-semibold tabular-nums">{data.score}<span className="text-lg text-muted"> / {data.max_score}</span></p>
        </div>
        <div><p className="text-sm text-muted">Correct</p><p className="text-xl font-medium text-ok tabular-nums">{data.correct}</p></div>
        <div><p className="text-sm text-muted">Wrong</p><p className="text-xl font-medium text-bad tabular-nums">{data.wrong}</p></div>
        <div><p className="text-sm text-muted">Left blank</p><p className="text-xl font-medium tabular-nums">{data.unanswered}</p></div>
        <p className="text-xs text-muted sm:col-span-4">
          Wrong answers cost {data.negative_mark} mark each. Accuracy on answered questions:{" "}
          {answered ? Math.round(((data.correct ?? 0) / answered) * 100) : 0}%.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Bars title="By section" rows={data.by_section} />
        <section className="card space-y-3 p-5">
          <h2 className="h2">Topics to revise</h2>
          {weakest.length === 0 && <p className="text-sm text-muted">Not enough questions per topic to rank yet.</p>}
          {weakest.map((t) => (
            <p key={String(t.id)} className="flex justify-between gap-3 text-sm">
              <span className="truncate">{t.label}</span>
              <span className="shrink-0 tabular-nums text-muted">{t.correct}/{t.total}</span>
            </p>
          ))}
        </section>
      </div>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="h2">Review</h2>
          <div className="flex gap-1" role="group" aria-label="Filter questions">
            {(["all", "wrong", "unanswered", "flagged"] as Filter[]).map((f) => (
              <button key={f} onClick={() => setFilter(f)} aria-pressed={filter === f}
                className={`rounded-full border px-3 py-1 text-xs capitalize ${filter === f ? "border-accent bg-accent-soft text-accent" : "border-line text-muted"}`}>
                {f}
              </button>
            ))}
          </div>
        </div>
        {shown.length === 0 && <p className="text-sm text-muted">Nothing to show for this filter.</p>}
        {shown.map((r) => (
          <article key={r.id} className="card space-y-4 p-5">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-medium">
                Q{data.review.indexOf(r) + 1}
                <span className={`ml-2 ${r.is_correct ? "text-ok" : r.is_correct === false ? "text-bad" : "text-muted"}`}>
                  {r.is_correct ? "Correct" : r.is_correct === false ? "Wrong" : "Not answered"}
                  {r.marks_awarded !== null && r.marks_awarded !== 0 && ` (${r.marks_awarded > 0 ? "+" : ""}${r.marks_awarded})`}
                </span>
              </p>
              <div className="flex gap-2">
                <Link href={`/chat?q=${r.id}`} className="btn px-3 py-1 text-xs">Ask AI</Link>
                <button className="btn px-3 py-1 text-xs" onClick={() => toggle(r.id)} aria-pressed={ids.has(r.id)}>
                  {ids.has(r.id) ? "Bookmarked" : "Bookmark"}
                </button>
              </div>
            </div>
            <QuestionView q={r} selected={r.response.selected} correct={r.correct_label} />
            <details open={r.is_correct !== true} className="rounded-lg border border-line px-4 py-3">
              <summary className="cursor-pointer text-sm font-medium">Solution</summary>
              <div className="mt-3"><SolutionPanel r={r} /></div>
            </details>
          </article>
        ))}
      </section>
    </div>
  );
}
