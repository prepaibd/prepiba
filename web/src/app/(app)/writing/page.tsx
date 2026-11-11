"use client";

import { useEffect, useMemo, useState } from "react";
import { MathText } from "@/components/math-text";
import { UsageBadge } from "@/components/usage-badge";
import { ApiError, get, post } from "@/lib/api";
import type { Paginated, Usage, WritingFeedback, WritingPrompt, WritingSubmission } from "@/lib/types";

// Mirrors WRITING_MIN_WORDS / WRITING_MAX_WORDS on the server, which is what actually enforces them.
const MIN_WORDS = 30;
const MAX_WORDS = 1200;
const countWords = (t: string) => (t.match(/\b[\w'’-]+\b/g) ?? []).length;

function Score({ label, value }: { label: string; value: number }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm"><span>{label}</span><span className="tabular-nums">{value}/10</span></div>
      <div className="h-2 overflow-hidden rounded-full bg-surface-2" role="img" aria-label={`${label} ${value} out of 10`}>
        <div className="h-full rounded-full bg-accent" style={{ width: `${value * 10}%` }} />
      </div>
    </div>
  );
}

function Feedback({ fb }: { fb: WritingFeedback }) {
  return (
    <div className="card space-y-5 p-5">
      <div className="flex items-end gap-3">
        <p className="text-4xl font-semibold tabular-nums">{fb.overall}<span className="text-lg text-muted">/10</span></p>
        <p className="pb-1 text-sm text-muted">Practice feedback, not an official mark.</p>
      </div>
      <p className="text-sm">{fb.summary}</p>
      <div className="grid gap-3 sm:grid-cols-3">
        <Score label="Content" value={fb.content} />
        <Score label="Structure" value={fb.structure} />
        <Score label="Language" value={fb.language} />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <h3 className="mb-1 text-sm font-medium text-ok">Strengths</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm">{fb.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
        <div>
          <h3 className="mb-1 text-sm font-medium text-warn">To improve</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm">{fb.improvements.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
      </div>
      {fb.corrections.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-medium">Corrections</h3>
          <ul className="space-y-2 text-sm">
            {fb.corrections.map((c, i) => (
              <li key={i} className="rounded-lg bg-surface-2 px-3 py-2">
                <span className="text-bad line-through">{c.original}</span> → <span className="font-medium text-ok">{c.suggestion}</span>
                {c.reason && <span className="block text-muted">{c.reason}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function Writing() {
  const [prompts, setPrompts] = useState<WritingPrompt[]>([]);
  const [history, setHistory] = useState<WritingSubmission[]>([]);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [promptId, setPromptId] = useState("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<WritingSubmission | null>(null);

  const loadMeta = () => {
    get<Paginated<WritingSubmission>>("/writing/submissions/", { page_size: 20 }).then((d) => setHistory(d.results)).catch(() => {});
    get<Usage>("/ai/usage/").then(setUsage).catch(() => {});
  };

  useEffect(() => {
    get<WritingPrompt[]>("/writing/prompts/")
      .then((p) => { setPrompts(p); if (p.length) setPromptId(p[0].id); })
      .catch(() => setError("Could not load writing prompts."));
    loadMeta();
  }, []);

  const prompt = useMemo(() => prompts.find((p) => p.id === promptId), [prompts, promptId]);
  const words = countWords(body);
  const tooShort = words < MIN_WORDS;
  const tooLong = words > MAX_WORDS;

  async function submit() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await post<WritingSubmission>("/writing/submissions/", { question_id: promptId, body }));
    } catch (e) {
      if (e instanceof ApiError) {
        const saved = (e.data as { submission?: WritingSubmission } | null)?.submission;
        setError(e.message);
        if (saved) setResult(saved);
      } else setError("Could not reach the server.");
    }
    setBusy(false);
    loadMeta();
  }

  async function retry(id: string) {
    setBusy(true);
    setError(null);
    try { setResult(await post<WritingSubmission>(`/writing/submissions/${id}/retry/`)); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Could not reach the server."); }
    setBusy(false);
    loadMeta();
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="h1">Writing practice</h1>
          <p className="text-muted">Answer a real past-paper writing task and get AI feedback.</p>
        </div>
        <UsageBadge item={usage?.writing} noun="reviews" />
      </div>

      <div className="card space-y-4 p-5">
        <label className="block space-y-1 text-sm">
          <span className="font-medium">Task</span>
          <select className="input" value={promptId} onChange={(e) => { setPromptId(e.target.value); setResult(null); }}>
            {prompts.map((p) => (
              <option key={p.id} value={p.id}>{p.session} · {p.type === "essay" ? "Essay" : "Argument"} {p.number}</option>
            ))}
          </select>
        </label>
        {prompt && (
          <div className="rounded-lg bg-surface-2 px-4 py-3 text-sm">
            {prompt.instruction && <p className="mb-2 text-muted"><MathText text={prompt.instruction} /></p>}
            <MathText text={prompt.stem} />
          </div>
        )}
        <label className="block space-y-1 text-sm">
          <span className="font-medium">Your answer</span>
          <textarea className="input min-h-[14rem]" value={body} onChange={(e) => setBody(e.target.value)}
            placeholder="Write here…" disabled={busy} />
        </label>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className={`text-sm tabular-nums ${tooLong ? "text-bad" : "text-muted"}`}>
            {words} words {tooShort && body ? `(at least ${MIN_WORDS})` : tooLong ? `(at most ${MAX_WORDS})` : ""}
          </p>
          <button className="btn btn-primary" onClick={submit} disabled={busy || tooShort || tooLong || !promptId}>
            {busy ? "Reviewing…" : "Get feedback"}
          </button>
        </div>
        {error && <p role="alert" className="text-sm text-bad">{error}</p>}
      </div>

      {result?.status === "failed" && (
        <div className="card flex items-center justify-between gap-3 p-4 text-sm">
          <span>Your text was saved, but the review did not finish.</span>
          <button className="btn" onClick={() => retry(result.id)} disabled={busy}>Try again</button>
        </div>
      )}
      {result?.feedback && <Feedback fb={result.feedback} />}

      {history.length > 0 && (
        <section className="space-y-2">
          <h2 className="h2">Your previous attempts</h2>
          {history.map((h) => (
            <button key={h.id} className="card flex w-full items-center justify-between p-4 text-left hover:bg-surface-2"
              onClick={() => { setResult(h); window.scrollTo({ top: 0, behavior: "smooth" }); }}>
              <span className="text-sm">{h.prompt.session} · {h.prompt.type} · {h.word_count} words
                <span className="ml-2 text-xs text-muted">{new Date(h.created_at).toLocaleDateString()}</span></span>
              <span className="text-sm tabular-nums">{h.feedback ? `${h.feedback.overall}/10` : "not reviewed"}</span>
            </button>
          ))}
        </section>
      )}
    </div>
  );
}
