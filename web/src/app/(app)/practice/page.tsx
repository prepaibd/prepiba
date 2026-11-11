"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { ApiError, get, post } from "@/lib/api";
import type { AttemptDetail, Exam, Subject, Topic } from "@/lib/types";

const TYPES = [
  "problem_solving", "data_sufficiency", "puzzle", "critical_reasoning", "fill_blank", "sentence_correction",
  "error_identification", "word_substitution", "reading_comp", "synonym", "antonym", "passage_completion",
];
const label = (s: string) => s.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

function PracticeInner() {
  const router = useRouter();
  const params = useSearchParams();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [subject, setSubject] = useState(params.get("subject") ?? "");
  const [tab, setTab] = useState<"custom" | "paper">("custom");
  const [exams, setExams] = useState<Exam[]>([]);
  const [examSlug, setExamSlug] = useState("");
  const [type, setType] = useState("");
  const [picked, setPicked] = useState<string[]>([]);
  const [count, setCount] = useState(20);
  const [timed, setTimed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    get<Subject[]>("/subjects/").then(setSubjects).catch(() => setError("Could not load subjects."));
    get<Topic[]>("/topics/").then(setTopics).catch(() => setError("Could not load topics."));
    get<Exam[]>("/exams/").then((e) => { setExams(e); setExamSlug((s) => s || e[0]?.slug || ""); }).catch(() => setError("Could not load papers."));
  }, []);

  const visibleTopics = useMemo(() => topics.filter((t) => !subject || t.subject === subject), [topics, subject]);

  function toggle(id: string) {
    setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));
  }

  async function start(override?: Record<string, unknown>) {
    setBusy(true);
    setError(null);
    const body = override ? { exam: examSlug, ...override } : picked.length
      ? { mode: "topic", topics: picked, count, timed, ...(type ? { type } : {}) }
      : { mode: "custom", count, timed, ...(subject ? { subject } : {}), ...(type ? { type } : {}) };
    try {
      const a = await post<AttemptDetail>("/attempts/", body);
      router.push(`/attempt/${a.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not start practice.");
      setBusy(false);
    }
  }

  const exam = exams.find((e) => e.slug === examSlug);
  const [sections, setSections] = useState<{ section_no: number; label: string; subject: string; scorable_count: number }[]>([]);
  useEffect(() => {
    if (!examSlug) return;
    let live = true;
    get<Exam>(`/exams/${examSlug}/`).then((e) => { if (live) setSections((e.sections ?? []).filter((x) => x.scorable_count > 0)); }).catch(() => {});
    return () => { live = false; };
  }, [examSlug]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="h1">Practice</h1>
        <p className="text-muted">Build a custom set, or sit a real paper as a timed mock. Only questions with a trusted answer key are scored.</p>
      </div>

      <div className="flex w-fit gap-1 rounded-lg bg-surface-2 p-1" role="tablist">
        {([["custom", "Custom set"], ["paper", "Full paper mock"]] as const).map(([t, l]) => (
          <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
            className={`rounded-md px-3 py-1 text-sm ${tab === t ? "bg-surface font-medium shadow-sm" : "text-muted"}`}>{l}</button>
        ))}
      </div>

      {tab === "paper" && (
        <div className="card space-y-5 p-5">
          <label className="block space-y-1 text-sm">
            <span className="font-medium">Past paper</span>
            <select className="input max-w-xs" value={examSlug} onChange={(e) => setExamSlug(e.target.value)}>
              {exams.map((e) => <option key={e.slug} value={e.slug}>{e.session}{e.completeness === "partial" ? " (partial)" : ""}</option>)}
            </select>
          </label>
          <p className="text-sm text-muted">
            A timed mock uses a {exam?.duration_minutes ?? 90} minute limit and negative marking. Untimed practice has no clock.
            {exam && ` ${exam.scorable_count} scored questions.`}
          </p>
          <div className="flex flex-wrap gap-2">
            <button className="btn btn-primary" disabled={busy || !examSlug} onClick={() => start({ mode: "mock_full" })}>Start timed mock</button>
            <button className="btn" disabled={busy || !examSlug} onClick={() => start({ mode: "past_paper" })}>Practise untimed</button>
          </div>
          {sections.length > 1 && (
            <div className="space-y-2 border-t border-line pt-4">
              <p className="text-sm font-medium">Or just one section</p>
              <div className="flex flex-wrap gap-2">
                {sections.map((s) => (
                  <button key={s.section_no} className="btn px-3 py-1 text-xs" disabled={busy}
                    onClick={() => start({ mode: "sectional", section_no: s.section_no })}>
                    {s.section_no}. {s.label || s.subject} · {s.scorable_count}
                  </button>
                ))}
              </div>
            </div>
          )}
          {error && <p role="alert" className="text-sm text-bad">{error}</p>}
        </div>
      )}

      {tab === "custom" && <div className="card space-y-5 p-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-1 text-sm">
            <span className="font-medium">Subject</span>
            <select className="input" value={subject} onChange={(e) => { setSubject(e.target.value); setPicked([]); }}>
              <option value="">All subjects</option>
              {subjects.filter((s) => s.slug !== "writing").map((s) => <option key={s.id} value={s.slug}>{s.name}</option>)}
            </select>
          </label>
          <label className="space-y-1 text-sm">
            <span className="font-medium">Question type</span>
            <select className="input" value={type} onChange={(e) => setType(e.target.value)}>
              <option value="">Any type</option>
              {TYPES.map((t) => <option key={t} value={t}>{label(t)}</option>)}
            </select>
          </label>
        </div>

        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">Topics <span className="font-normal text-muted">(optional)</span></legend>
          <div className="flex flex-wrap gap-2">
            {visibleTopics.map((t) => {
              const on = picked.includes(t.id);
              return (
                <button key={t.id} type="button" aria-pressed={on} onClick={() => toggle(t.id)}
                  className={`rounded-full border px-3 py-1 text-xs ${on ? "border-accent bg-accent-soft text-accent" : "border-line text-muted hover:text-ink"}`}>
                  {t.name}
                </button>
              );
            })}
          </div>
        </fieldset>

        <div className="flex flex-wrap items-center gap-6">
          <label className="flex items-center gap-2 text-sm">
            <span className="font-medium">Questions</span>
            <input className="input w-20" type="number" min={1} max={100} value={count}
              onChange={(e) => setCount(Math.max(1, Math.min(100, Number(e.target.value) || 1)))} />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={timed} onChange={(e) => setTimed(e.target.checked)} />
            Timed (1 minute per question)
          </label>
        </div>

        <button className="btn btn-primary" onClick={() => start()} disabled={busy}>Start practice</button>
        {error && <p role="alert" className="text-sm text-bad">{error}</p>}
      </div>}
    </div>
  );
}

export default function Practice() {
  return <Suspense fallback={<p className="text-sm text-muted">Loading…</p>}><PracticeInner /></Suspense>;
}
