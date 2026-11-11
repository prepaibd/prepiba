"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiError, get, post } from "@/lib/api";
import type { AttemptDetail, Overview, TopicFrequency } from "@/lib/types";

const SUBJECT: Record<string, string> = {
  language: "Language & Communication", mathematics: "Mathematics", analytical: "Analytical Ability",
};
const pct = (x: number) => `${Math.round(x * 100)}%`;
const mins = (s: number) => (s >= 60 ? `${Math.floor(s / 60)}m ${s % 60}s` : `${s}s`);

function Stat({ label, value }: { label: string; value: string }) {
  return <div className="card p-4"><p className="text-sm text-muted">{label}</p><p className="text-2xl font-semibold tabular-nums">{value}</p></div>;
}

function Trend({ points }: { points: Overview["trend"] }) {
  if (points.length < 2) return <p className="text-sm text-muted">Finish two attempts to see your trend.</p>;
  const W = 600, H = 140, P = 12;
  const lo = Math.min(0, ...points.map((p) => p.score_pct));
  const hi = Math.max(100, ...points.map((p) => p.score_pct));
  const x = (i: number) => P + (i * (W - 2 * P)) / (points.length - 1);
  const y = (v: number) => H - P - ((v - lo) / (hi - lo)) * (H - 2 * P);
  const d = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.score_pct).toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img"
      aria-label={`Score trend over your last ${points.length} attempts, from ${points[0].score_pct}% to ${points.at(-1)!.score_pct}%`}>
      <line x1={P} x2={W - P} y1={y(0)} y2={y(0)} stroke="var(--line)" />
      <path d={d} fill="none" stroke="var(--accent)" strokeWidth="2.5" strokeLinejoin="round" />
      {points.map((p, i) => <circle key={p.attempt_id} cx={x(i)} cy={y(p.score_pct)} r="3.5" fill="var(--accent)"><title>{`${p.score_pct}%`}</title></circle>)}
    </svg>
  );
}

function Heatmap({ data }: { data: TopicFrequency }) {
  const [all, setAll] = useState(false);
  const rows = all ? data.topics : data.topics.slice(0, 12);
  const max = Math.max(1, ...data.topics.flatMap((t) => Object.values(t.by_year)));
  return (
    <div className="space-y-3">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[34rem] border-separate border-spacing-0.5 text-xs">
          <thead>
            <tr><th className="text-left font-medium text-muted">Topic</th>
              {data.years.map((y) => <th key={y} className="w-9 font-medium text-muted">{String(y).slice(2)}</th>)}
              <th className="font-medium text-muted">Total</th></tr>
          </thead>
          <tbody>
            {rows.map((t) => (
              <tr key={t.id}>
                <td className="max-w-[16rem] truncate pr-2" title={t.name}>{t.name}</td>
                {data.years.map((y) => {
                  const n = t.by_year[y] ?? 0;
                  return (
                    <td key={y} className="h-7 rounded text-center tabular-nums"
                      style={{ background: n ? `color-mix(in srgb, var(--accent) ${Math.round(15 + (n / max) * 75)}%, transparent)` : "var(--surface-2)" }}>
                      {n || ""}
                    </td>
                  );
                })}
                <td className="text-center font-medium tabular-nums">{t.total}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.topics.length > 12 && <button className="btn text-xs" onClick={() => setAll(!all)}>{all ? "Show fewer" : `Show all ${data.topics.length} topics`}</button>}
    </div>
  );
}

export default function Analytics() {
  const router = useRouter();
  const [o, setO] = useState<Overview | null>(null);
  const [freq, setFreq] = useState<TopicFrequency | null>(null);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    get<Overview>("/analytics/overview/").then(setO).catch(() => setError(true));
    get<TopicFrequency>("/analytics/topic-frequency/").then(setFreq).catch(() => {});
  }, []);

  async function practise(topicId: string) {
    setBusy(topicId);
    try {
      const a = await post<AttemptDetail>("/attempts/", { mode: "topic", topics: [topicId], count: 15 });
      router.push(`/attempt/${a.id}`);
    } catch (e) {
      setError(!(e instanceof ApiError));
      setBusy(null);
    }
  }

  if (error) return <p role="alert" className="text-bad">Could not load your analytics.</p>;
  if (!o) return <p className="text-sm text-muted">Loading…</p>;
  const t = o.totals;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="h1">Analytics</h1>
        <p className="text-muted">Based on your finished attempts. Blank answers are not counted.</p>
      </div>

      {t.attempts === 0 ? (
        <div className="card p-6 text-sm">
          <p className="mb-3">You have not finished an attempt yet, so there is nothing to analyse.</p>
          <Link href="/papers" className="btn btn-primary">Take a past paper</Link>
        </div>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-5">
            <Stat label="Attempts" value={String(t.attempts)} />
            <Stat label="Questions answered" value={String(t.answered)} />
            <Stat label="Accuracy" value={pct(t.accuracy)} />
            <Stat label="Avg time / question" value={mins(t.avg_seconds_per_question)} />
            <Stat label="Day streak" value={String(t.streak_days)} />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <section className="card space-y-3 p-5">
              <h2 className="h2">Accuracy by subject</h2>
              {o.by_subject.map((s) => (
                <div key={s.subject} className="space-y-1">
                  <div className="flex justify-between text-sm"><span>{SUBJECT[s.subject] ?? s.subject}</span>
                    <span className="tabular-nums text-muted">{s.correct}/{s.answered} · {pct(s.accuracy)}</span></div>
                  <div className="h-2 overflow-hidden rounded-full bg-surface-2" role="img" aria-label={`${pct(s.accuracy)} correct`}>
                    <div className="h-full rounded-full bg-accent" style={{ width: pct(s.accuracy) }} />
                  </div>
                </div>
              ))}
            </section>
            <section className="card space-y-3 p-5">
              <h2 className="h2">Score trend</h2>
              <Trend points={o.trend} />
            </section>
          </div>

          <section className="card space-y-3 p-5">
            <h2 className="h2">Topics to work on</h2>
            {o.weakest.length === 0 && <p className="text-sm text-muted">Answer at least {o.min_answers_for_weak} questions in a topic to see it here.</p>}
            {o.weakest.map((w) => (
              <div key={w.topic_id} className="flex flex-wrap items-center justify-between gap-3 text-sm">
                <span className="min-w-0 flex-1"><span className="block truncate font-medium">{w.topic}</span>
                  <span className="text-muted">{w.correct}/{w.answered} correct · {mins(w.avg_seconds)} avg</span></span>
                <button className="btn px-3 py-1 text-xs" disabled={busy !== null} onClick={() => practise(w.topic_id)}>
                  {busy === w.topic_id ? "Starting…" : "Practise 15"}
                </button>
              </div>
            ))}
          </section>
        </>
      )}

      {freq && (
        <section className="card space-y-3 p-5">
          <div>
            <h2 className="h2">What past papers test</h2>
            <p className="text-sm text-muted">Questions per topic in each paper year (columns are years). Darker means more questions.</p>
          </div>
          <Heatmap data={freq} />
        </section>
      )}
    </div>
  );
}
