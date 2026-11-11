"use client";

import { useParams, useRouter } from "next/navigation";
import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import { GroupContext, QuestionView, startsGroup } from "@/components/question-view";
import { ApiError, get, post } from "@/lib/api";
import type { AttemptDetail, Response } from "@/lib/types";

const pad = (n: number) => String(n).padStart(2, "0");
const clock = (s: number) => `${Math.floor(s / 3600) > 0 ? pad(Math.floor(s / 3600)) + ":" : ""}${pad(Math.floor((s % 3600) / 60))}:${pad(s % 60)}`;

export default function AttemptPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [attempt, setAttempt] = useState<AttemptDetail | null>(null);
  const [resp, setResp] = useState<Record<string, Response>>({});
  const [idx, setIdx] = useState(0); // the question being read: time is credited to it
  const [remaining, setRemaining] = useState<number | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveFailed, setSaveFailed] = useState(false);

  const skew = useRef(0); // server clock minus client clock, ms
  const deadline = useRef<number | null>(null);
  const pending = useRef<Record<string, number>>({}); // seconds spent but not yet sent, by question
  const idxRef = useRef(0);
  const finishing = useRef(false);

  useEffect(() => { idxRef.current = idx; }, [idx]);

  useEffect(() => {
    get<AttemptDetail>(`/attempts/${id}/`)
      .then((a) => {
        if (a.status !== "in_progress") { router.replace(`/results/${id}`); return; }
        skew.current = Date.parse(a.server_now) - Date.now();
        deadline.current = a.deadline_at ? Date.parse(a.deadline_at) : null;
        setResp(Object.fromEntries(a.questions.map((q) => [q.id, q.response])));
        setAttempt(a);
      })
      .catch((e) => setError(e instanceof ApiError && e.status === 404 ? "Attempt not found." : "Could not load the attempt."));
  }, [id, router]);

  const flush = useCallback(async () => {
    const entries = Object.entries(pending.current).filter(([, s]) => s > 0);
    pending.current = {};
    await Promise.all(entries.map(([question, time_spent]) =>
      post(`/attempts/${id}/answers/`, { question, time_spent }).catch(() => {
        pending.current[question] = (pending.current[question] ?? 0) + time_spent; // retry next time
      })));
  }, [id]);

  const finish = useCallback(async () => {
    if (finishing.current) return;
    finishing.current = true;
    setBusy(true);
    try {
      await flush();
      await post(`/attempts/${id}/submit/`);
      router.replace(`/results/${id}`);
    } catch {
      finishing.current = false;
      setBusy(false);
      setError("Could not submit. Check your connection and try again.");
    }
  }, [flush, id, router]);

  // One clock: counts down, tracks per-question time, and auto-submits at zero.
  useEffect(() => {
    if (!attempt) return;
    const t = setInterval(() => {
      const q = attempt.questions[idxRef.current];
      if (q) pending.current[q.id] = (pending.current[q.id] ?? 0) + 1;
      if (deadline.current !== null) {
        const left = Math.max(0, Math.floor((deadline.current - (Date.now() + skew.current)) / 1000));
        setRemaining(left);
        if (left === 0) finish();
      }
    }, 1000);
    return () => clearInterval(t);
  }, [attempt, finish]);

  const save = useCallback(async (question: string, body: Record<string, unknown>) => {
    try {
      await post(`/attempts/${id}/answers/`, { question, ...body });
      setSaveFailed(false);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) router.replace(`/results/${id}`);
      else setSaveFailed(true);
    }
  }, [id, router]);

  // Credit time to whichever question is under the top of the viewport.
  useEffect(() => {
    if (!attempt) return;
    const seen = new Map<Element, boolean>();
    const obs = new IntersectionObserver((entries) => {
      entries.forEach((e) => seen.set(e.target, e.isIntersecting));
      const first = attempt.questions.findIndex((x) => seen.get(document.getElementById(`aq-${x.id}`) as Element));
      if (first >= 0) setIdx(first);
    }, { rootMargin: "-90px 0px -55% 0px" });
    attempt.questions.forEach((x) => { const el = document.getElementById(`aq-${x.id}`); if (el) obs.observe(el); });
    return () => obs.disconnect();
  }, [attempt]);

  const goTo = useCallback((id: string) => {
    flush();
    document.getElementById(`aq-${id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [flush]);

  const choose = useCallback((qid: string, label: string) => {
    const next = resp[qid]?.selected === label ? "" : label; // tap again to clear
    setResp((r) => ({ ...r, [qid]: { ...r[qid], selected: next || null } }));
    save(qid, { option: next });
  }, [resp, save]);

  const flag = useCallback((qid: string) => {
    const on = !resp[qid]?.flagged;
    setResp((r) => ({ ...r, [qid]: { ...r[qid], flagged: on } }));
    save(qid, { flagged: on });
  }, [resp, save]);

  if (error && !attempt) return <p role="alert" className="p-8 text-bad">{error}</p>;
  if (!attempt) return <div className="grid flex-1 place-items-center text-sm text-muted">Loading…</div>;

  const qs = attempt.questions;
  const total = qs.length;
  const answered = qs.filter((x) => resp[x.id]?.selected).length;
  const low = remaining !== null && remaining <= 300;

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-10 flex items-center gap-4 border-b border-line bg-surface px-4 py-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{attempt.exam ? attempt.exam.session : "Practice"}</p>
          <p className="text-xs text-muted">{answered} of {total} answered</p>
        </div>
        {remaining !== null && (
          <p className={`font-mono text-lg tabular-nums ${low ? "text-bad" : ""}`} role="timer" aria-label="Time remaining">
            {clock(remaining)}
          </p>
        )}
        <button className="btn btn-primary" onClick={() => setConfirming(true)} disabled={busy}>Submit</button>
      </header>

      <div className="mx-auto grid w-full max-w-6xl flex-1 gap-6 px-4 py-6 lg:grid-cols-[1fr_260px]">
        <section className="min-w-0 space-y-5">
          {qs.map((q, i) => {
            const r = resp[q.id];
            return (
              <Fragment key={q.id}>
                {startsGroup(q, qs[i - 1]) && <div className="card space-y-4 border-dashed p-4"><GroupContext g={q.group} /></div>}
                <article id={`aq-${q.id}`} className="card scroll-mt-20 space-y-4 p-5">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium text-muted">Question {i + 1} of {total}</p>
                    <button className={`btn px-3 py-1 text-xs ${r?.flagged ? "border-warn bg-warn-soft text-warn" : ""}`}
                      onClick={() => flag(q.id)} aria-pressed={!!r?.flagged}>
                      {r?.flagged ? "Flagged" : "Flag for review"}
                    </button>
                  </div>
                  <QuestionView q={q} showGroup={false} selected={r?.selected} onSelect={(l) => choose(q.id, l)} />
                </article>
              </Fragment>
            );
          })}
          {saveFailed && <p role="alert" className="text-sm text-bad">Your last answer could not be saved. It will retry when you answer again.</p>}
          {error && <p role="alert" className="text-sm text-bad">{error}</p>}
          <div className="flex justify-end pt-2">
            <button className="btn btn-primary" onClick={() => setConfirming(true)} disabled={busy}>Submit attempt</button>
          </div>
        </section>

        <aside className="space-y-3 lg:sticky lg:top-20 lg:self-start" aria-label="Question palette">
          <div className="card grid grid-cols-6 gap-1.5 p-3 sm:grid-cols-8 lg:grid-cols-5">
            {qs.map((x, i) => {
              const r = resp[x.id];
              const tone = i === idx ? "border-accent ring-2 ring-accent"
                : r?.flagged ? "border-warn bg-warn-soft"
                : r?.selected ? "border-accent bg-accent-soft" : "border-line";
              return (
                <button key={x.id} onClick={() => goTo(x.id)} aria-label={`Question ${i + 1}${r?.selected ? ", answered" : ""}${r?.flagged ? ", flagged" : ""}`}
                  className={`h-9 rounded-md border text-xs tabular-nums ${tone}`}>{i + 1}</button>
              );
            })}
          </div>
          <p className="text-xs text-muted">
            Tap an option again to clear it. Wrong answers lose {attempt.negative_mark} mark; blanks lose nothing.
          </p>
        </aside>
      </div>

      {confirming && (
        <div className="fixed inset-0 z-20 grid place-items-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-label="Confirm submit">
          <div className="card w-full max-w-sm space-y-4 p-6">
            <h2 className="h2">Submit your attempt?</h2>
            <p className="text-sm text-muted">
              You have answered {answered} of {total} questions
              {total - answered > 0 && <> and left <b className="text-ink">{total - answered}</b> blank</>}.
              You cannot change answers after submitting.
            </p>
            <div className="flex justify-end gap-2">
              <button className="btn" onClick={() => setConfirming(false)} disabled={busy}>Keep working</button>
              <button className="btn btn-primary" onClick={finish} disabled={busy}>{busy ? "Submitting…" : "Submit now"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
