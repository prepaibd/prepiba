"use client";

import { useCallback, useEffect, useState } from "react";
import { MathText } from "@/components/math-text";
import { useAuth } from "@/hooks/use-auth";
import { ApiError, api, get } from "@/lib/api";
import type { Paginated, ReviewQuestion, ReviewSummary } from "@/lib/types";

const PAGE = 15;

function AnswerVerify({ q, onSaved }: { q: ReviewQuestion; onSaved: (q: ReviewQuestion) => void }) {
  const current = q.options.find((o) => o.is_correct)?.label ?? "";
  const [label, setLabel] = useState(current);
  const [status, setStatus] = useState(q.answer_status === "none" ? "unverified" : q.answer_status);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  if (q.options.length === 0) return null;

  async function save() {
    setBusy(true);
    setMsg(null);
    try {
      onSaved(await api<ReviewQuestion>(`/review/questions/${q.id}/answer/`, {
        method: "POST", body: { answer_status: status, ...(label ? { correct_label: label } : {}) },
      }));
      setMsg("Saved");
    } catch (e) { setMsg(e instanceof ApiError ? JSON.stringify(e.data) : "Could not save."); }
    setBusy(false);
  }

  return (
    <fieldset className="space-y-2 rounded-lg border border-line p-3">
      <legend className="px-1 text-xs font-medium uppercase tracking-wide text-muted">Answer key · now {q.answer_status}</legend>
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <label className="flex items-center gap-1">Correct option
          <select className="input w-auto" value={label} onChange={(e) => setLabel(e.target.value)}>
            <option value="">—</option>{q.options.map((o) => <option key={o.label} value={o.label}>{o.label}</option>)}
          </select></label>
        <label className="flex items-center gap-1">Status
          <select className="input w-auto" value={status} onChange={(e) => setStatus(e.target.value)}>
            {["verified", "derived", "unverified", "disputed"].map((x) => <option key={x}>{x}</option>)}
          </select></label>
        <button className="btn" disabled={busy} onClick={save}>Save answer</button>
        {msg && <span className="text-xs text-muted">{msg}</span>}
      </div>
      <p className="text-xs text-muted">Verified and derived keys are scored; disputed and unverified are not.</p>
    </fieldset>
  );
}

function Editor({ q, onSaved }: { q: ReviewQuestion; onSaved: (q: ReviewQuestion) => void }) {
  const [stem, setStem] = useState(q.stem_bn);
  const [opts, setOpts] = useState<Record<string, string>>(Object.fromEntries(q.options.map((o) => [o.label, o.text_bn])));
  const [sol, setSol] = useState(q.solution_bn);
  const [problems, setProblems] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  async function save(status: "draft" | "reviewed" | null) {
    setBusy(true);
    setProblems([]);
    try {
      const body: Record<string, unknown> = { stem_bn: stem, options_bn: opts, solution_body_bn: sol };
      if (status) body.bn_status = status;
      onSaved(await api<ReviewQuestion>(`/review/questions/${q.id}/`, { method: "PATCH", body }));
    } catch (e) {
      if (e instanceof ApiError && e.data && typeof e.data === "object") {
        const d = e.data as Record<string, unknown>;
        const list = (d.fidelity as string[] | undefined) ?? Object.values(d).flat().map(String);
        setProblems(list);
      } else setProblems(["Could not save."]);
    }
    setBusy(false);
  }

  return (
    <div className="card space-y-4 p-5">
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <p className="font-medium">{q.session} · section {q.section_no} · Q{q.number} <span className="chip ml-2">{q.type.replace(/_/g, " ")}</span></p>
        <span className="chip">{q.bn_status || "no Bangla"}</span>
      </div>
      {(q.source_defect || q.review_note) && (
        <p className="rounded-lg bg-warn-soft px-3 py-2 text-sm text-warn">{q.source_defect ? `Printed defect: ${q.source_defect}. ` : ""}{q.review_note}</p>
      )}
      {q.passage && <details><summary className="cursor-pointer text-sm text-muted">Passage</summary><p className="mt-2 text-sm"><MathText text={q.passage} /></p></details>}

      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wide text-muted">English</p>
          <p className="text-sm"><MathText text={q.stem} /></p>
          <ul className="space-y-1 text-sm">
            {q.options.map((o) => (
              <li key={o.label} className={o.is_correct ? "font-medium text-ok" : ""}>{o.label}. <MathText text={o.text} />{o.is_correct && " ✓"}</li>
            ))}
          </ul>
        </div>
        <div className="space-y-2">
          <label className="block text-xs font-medium uppercase tracking-wide text-muted" htmlFor={`stem-${q.id}`}>Bangla stem</label>
          <textarea id={`stem-${q.id}`} className="input min-h-[7rem]" value={stem} onChange={(e) => setStem(e.target.value)} />
          <p className="rounded-lg bg-surface-2 px-3 py-2 text-sm"><MathText text={stem} /></p>
        </div>
      </div>

      {q.options.some((o) => o.text_bn || true) && (
        <details>
          <summary className="cursor-pointer text-sm font-medium">Bangla options and solution</summary>
          <div className="mt-3 space-y-3">
            {q.options.map((o) => (
              <label key={o.label} className="block text-sm">
                <span className="text-muted">Option {o.label}</span>
                <input className="input" value={opts[o.label] ?? ""} onChange={(e) => setOpts({ ...opts, [o.label]: e.target.value })} />
              </label>
            ))}
            <label className="block text-sm">
              <span className="text-muted">Bangla solution</span>
              <textarea className="input min-h-[6rem]" value={sol} onChange={(e) => setSol(e.target.value)} />
            </label>
            {q.solution_en && <p className="text-sm text-muted">English solution: <MathText text={q.solution_en} /></p>}
          </div>
        </details>
      )}

      <AnswerVerify q={q} onSaved={onSaved} />

      {problems.length > 0 && (
        <ul role="alert" className="list-disc space-y-1 rounded-lg bg-bad-soft px-8 py-2 text-sm text-bad">
          {problems.map((p, i) => <li key={i}>{p}</li>)}
        </ul>
      )}
      <div className="flex flex-wrap gap-2">
        <button className="btn" disabled={busy} onClick={() => save(null)}>Save</button>
        <button className="btn btn-primary" disabled={busy || !stem.trim()} onClick={() => save("reviewed")}>Save &amp; mark reviewed</button>
        {q.bn_status === "reviewed" && <button className="btn" disabled={busy} onClick={() => save("draft")}>Back to draft</button>}
      </div>
    </div>
  );
}

export default function Review() {
  const { user } = useAuth();
  const allowed = user?.role === "reviewer" || user?.role === "admin";
  const [summary, setSummary] = useState<ReviewSummary | null>(null);
  const [filter, setFilter] = useState("draft");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Paginated<ReviewQuestion> | null>(null);
  const [error, setError] = useState(false);

  const load = useCallback(() => {
    get<ReviewSummary>("/review/questions/summary/").then(setSummary).catch(() => {});
    get<Paginated<ReviewQuestion>>("/review/questions/", {
      page, page_size: PAGE, search,
      ...(filter === "flagged" ? { flagged: 1 } : filter === "all" ? {} : { bn: filter }),
    }).then((d) => { setData(d); setError(false); }).catch(() => setError(true));
  }, [filter, search, page]);

  useEffect(() => { if (allowed) load(); }, [allowed, load]);

  if (!allowed) return <p className="text-muted">Reviewer access is required for this page.</p>;

  const pages = data ? Math.max(1, Math.ceil(data.count / PAGE)) : 1;
  return (
    <div className="space-y-6">
      <div>
        <h1 className="h1">Translation review</h1>
        <p className="text-muted">Check Bangla against the English. Numbers and LaTeX must match exactly; Bangla digits are not allowed.</p>
      </div>
      {summary && (
        <div className="grid gap-3 sm:grid-cols-4">
          {([["Draft", summary.bangla.draft], ["Reviewed", summary.bangla.reviewed], ["No Bangla", summary.bangla.missing], ["Flagged", summary.flagged]] as const).map(([l, n]) => (
            <div key={l} className="card p-4"><p className="text-sm text-muted">{l}</p><p className="text-2xl font-semibold tabular-nums">{n}</p></div>
          ))}
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        <select className="input w-auto" value={filter} aria-label="Filter" onChange={(e) => { setFilter(e.target.value); setPage(1); }}>
          <option value="draft">Draft translations</option><option value="reviewed">Reviewed</option>
          <option value="missing">Missing Bangla</option><option value="flagged">Flagged questions</option><option value="all">Everything</option>
        </select>
        <input className="input max-w-xs" placeholder="Search text…" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} aria-label="Search" />
      </div>
      {error && <p role="alert" className="text-sm text-bad">Could not load questions.</p>}
      {data?.results.map((q) => (
        <Editor key={`${q.id}-${q.bn_status}-${q.stem_bn}`} q={q}
          onSaved={(n) => { setData((d) => d && ({ ...d, results: d.results.map((x) => (x.id === n.id ? n : x)) })); get<ReviewSummary>("/review/questions/summary/").then(setSummary).catch(() => {}); }} />
      ))}
      {data && data.results.length === 0 && <p className="text-sm text-muted">Nothing matches.</p>}
      <div className="flex items-center justify-between">
        <button className="btn" disabled={page <= 1} onClick={() => setPage(page - 1)}>← Previous</button>
        <span className="text-sm text-muted">Page {page} of {pages}</span>
        <button className="btn" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next →</button>
      </div>
    </div>
  );
}
