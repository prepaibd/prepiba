"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Fragment, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { PastQuestion } from "@/components/past-question";
import { GroupContext, startsGroup } from "@/components/question-view";
import { useBookmarks } from "@/hooks/use-bookmarks";
import { get } from "@/lib/api";
import type { Exam, Paginated, Question, Section, Subject, Topic } from "@/lib/types";

const PAGE = 100;

function useDebounced<T>(value: T, ms: number) {
  const [v, setV] = useState(value);
  useEffect(() => { const t = setTimeout(() => setV(value), ms); return () => clearTimeout(t); }, [value, ms]);
  return v;
}

function PapersInner() {
  const router = useRouter();
  const params = useSearchParams();
  const { ids: saved, toggle } = useBookmarks();

  const [exams, setExams] = useState<Exam[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [meta, setMeta] = useState<"loading" | "ready" | "error">("loading");

  const [search, setSearch] = useState("");
  const term = useDebounced(search.trim(), 300);
  const searching = term.length >= 2;

  const view = params.get("view") === "topic" ? "topic" : "exam";
  const examSlug = params.get("exam") ?? exams[0]?.slug ?? "";
  const topicId = params.get("topic") ?? "";
  const subjectSlug = params.get("subject") ?? "";
  const sectionNo = params.get("section") ?? "";

  const nav = useCallback((next: Record<string, string>) => {
    router.replace(`/papers?${new URLSearchParams(next).toString()}`, { scroll: false });
  }, [router]);

  useEffect(() => {
    Promise.all([get<Exam[]>("/exams/"), get<Subject[]>("/subjects/"), get<Topic[]>("/topics/")])
      .then(([e, s, t]) => { setExams(e); setSubjects(s); setTopics(t); setMeta("ready"); })
      .catch(() => setMeta("error"));
  }, []);

  // Section chips for the selected exam.
  useEffect(() => {
    if (view !== "exam" || !examSlug) return;
    let live = true;
    get<Exam>(`/exams/${examSlug}/`).then((e) => { if (live) setSections((e.sections ?? []).filter((s) => s.question_count > 0)); }).catch(() => {});
    return () => { live = false; };
  }, [view, examSlug]);

  // What to list. The search box overrides the sidebar selection and looks across every paper.
  const query = useMemo(() => {
    if (searching) return { search: term };
    if (view === "exam") return examSlug ? { exam: examSlug, ...(sectionNo ? { section_no: sectionNo } : {}) } : null;
    if (topicId) return { topic: topicId };
    if (subjectSlug) return { subject: subjectSlug };
    return null;
  }, [searching, term, view, examSlug, sectionNo, topicId, subjectSlug]);
  const queryKey = JSON.stringify(query);

  const [items, setItems] = useState<Question[]>([]);
  const [count, setCount] = useState(0);
  const [nextPage, setNextPage] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);

  const fetchPage = useCallback(async (page: number, live: () => boolean) => {
    if (!query) return;
    setLoading(true);
    setFailed(false);
    try {
      const d = await get<Paginated<Question>>("/questions/", { ...query, page, page_size: PAGE });
      if (!live()) return;
      setItems((prev) => (page === 1 ? d.results : [...prev, ...d.results]));
      setCount(d.count);
      setNextPage(d.next ? page + 1 : null);
    } catch {
      if (live()) setFailed(true);
    } finally {
      if (live()) setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `query` is tracked through queryKey
  }, [queryKey]);

  useEffect(() => {
    let alive = true;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset the list when the selection changes
    setItems([]); setCount(0); setNextPage(null);
    fetchPage(1, () => alive);
    return () => { alive = false; };
  }, [fetchPage]);

  const sessionOf = useMemo(() => Object.fromEntries(exams.map((e) => [e.slug, e.session])), [exams]);
  const topicsBySubject = useMemo(
    () => subjects.map((s) => ({ s, list: topics.filter((t) => t.subject === s.slug) })).filter((x) => x.list.length > 0),
    [subjects, topics]);

  const exam = exams.find((e) => e.slug === examSlug);
  const topic = topics.find((t) => t.id === topicId);
  const subject = subjects.find((s) => s.slug === subjectSlug);
  const heading = searching ? `Search: “${term}”`
    : view === "exam" ? (exam ? `${exam.institute} ${exam.program.toUpperCase()} · ${exam.session}` : "Past papers")
    : topic ? topic.name : subject ? `All ${subject.name} topics` : "Pick a topic";
  const side = "w-full rounded-lg px-3 py-2 text-left text-sm";
  const sideTone = (on: boolean) => on ? "bg-accent-soft font-medium text-accent" : "hover:bg-surface-2";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="h1">Past papers</h1>
          <p className="text-muted">Every question from real IBA MBA papers. Browse by exam or by topic.</p>
        </div>
        <div className="relative w-full sm:w-80">
          <input className="input pr-9" type="search" placeholder="Search all questions…" value={search}
            onChange={(e) => setSearch(e.target.value)} aria-label="Search questions" />
          {search && (
            <button className="absolute right-2 top-1/2 -translate-y-1/2 px-1 text-muted hover:text-ink" onClick={() => setSearch("")} aria-label="Clear search">✕</button>
          )}
        </div>
      </div>

      {meta === "error" && <p role="alert" className="text-sm text-bad">Could not load papers.</p>}

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <aside className="space-y-3 lg:sticky lg:top-20 lg:max-h-[calc(100vh-6rem)] lg:self-start lg:overflow-y-auto">
          <div className="flex gap-1 rounded-lg bg-surface-2 p-1" role="tablist">
            {(["exam", "topic"] as const).map((v) => (
              <button key={v} role="tab" aria-selected={view === v}
                onClick={() => { setSearch(""); nav(v === "exam" ? {} : { view: "topic" }); }}
                className={`flex-1 rounded-md px-3 py-1 text-sm ${view === v ? "bg-surface font-medium shadow-sm" : "text-muted"}`}>
                {v === "exam" ? "By exam" : "By topic"}
              </button>
            ))}
          </div>

          {meta === "loading" && <p className="text-sm text-muted">Loading…</p>}

          {view === "exam" ? (
            <nav className="card space-y-0.5 p-1.5" aria-label="Exams">
              {exams.map((e) => (
                <button key={e.slug} aria-current={e.slug === examSlug ? "true" : undefined}
                  onClick={() => { setSearch(""); nav({ exam: e.slug }); }}
                  className={`${side} flex items-center justify-between gap-2 ${sideTone(!searching && e.slug === examSlug)}`}>
                  <span>{e.session}</span>
                  <span className="text-xs text-muted">{e.question_count}{e.completeness === "partial" ? " · partial" : ""}</span>
                </button>
              ))}
            </nav>
          ) : (
            <nav className="card space-y-1 p-1.5" aria-label="Topics">
              {topicsBySubject.map(({ s, list }) => (
                <details key={s.id} open={s.slug === subjectSlug || list.some((t) => t.id === topicId) || topicsBySubject.length === 1}>
                  <summary className="cursor-pointer rounded-lg px-3 py-2 text-sm font-medium hover:bg-surface-2">{s.name}</summary>
                  <div className="space-y-0.5 pb-1 pl-2">
                    <button onClick={() => { setSearch(""); nav({ view: "topic", subject: s.slug }); }}
                      className={`${side} ${sideTone(!searching && subjectSlug === s.slug && !topicId)}`}>All {s.name}</button>
                    {list.map((t) => (
                      <button key={t.id} onClick={() => { setSearch(""); nav({ view: "topic", topic: t.id }); }}
                        className={`${side} flex items-center justify-between gap-2 ${sideTone(!searching && topicId === t.id)}`}>
                        <span>{t.name}</span><span className="text-xs text-muted">{t.question_count}</span>
                      </button>
                    ))}
                  </div>
                </details>
              ))}
            </nav>
          )}
        </aside>

        <section className="min-w-0 space-y-4" aria-live="polite">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="h2 mr-2">{heading}</h2>
            {query && <span className="chip">{count} question{count === 1 ? "" : "s"}</span>}
          </div>

          {!searching && view === "exam" && sections.length > 1 && (
            <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Sections">
              {[{ section_no: 0, label: "All sections", subject: "" }, ...sections].map((s) => {
                const on = (sectionNo || "0") === String(s.section_no);
                return (
                  <button key={s.section_no} role="tab" aria-selected={on}
                    onClick={() => nav(s.section_no ? { exam: examSlug, section: String(s.section_no) } : { exam: examSlug })}
                    className={`rounded-full border px-3 py-1 text-xs ${on ? "border-accent bg-accent-soft text-accent" : "border-line text-muted hover:text-ink"}`}>
                    {s.section_no ? `${s.section_no}. ${s.label || s.subject}` : s.label}
                  </button>
                );
              })}
            </div>
          )}

          {!query && meta === "ready" && <p className="text-sm text-muted">Choose a topic on the left to list its questions.</p>}
          {query && !loading && !failed && items.length === 0 && (
            <p className="text-sm text-muted">{searching ? "No questions match your search." : "No questions here."}</p>
          )}

          {items.map((q, i) => (
            <Fragment key={q.id}>
              {startsGroup(q, items[i - 1]) && <div className="card space-y-4 border-dashed p-4"><GroupContext g={q.group} /></div>}
              <PastQuestion q={q} session={sessionOf[q.exam] ?? q.exam} saved={saved.has(q.id)} onToggleSave={() => toggle(q.id)} />
            </Fragment>
          ))}

          {loading && <p className="text-sm text-muted">Loading…</p>}
          {failed && (
            <p role="alert" className="text-sm text-bad">
              Could not load questions. <button className="underline" onClick={() => fetchPage(nextPage ?? 1, () => true)}>Retry</button>
            </p>
          )}
          {nextPage && !loading && (
            <button className="btn w-full" onClick={() => fetchPage(nextPage, () => true)}>
              Load more ({count - items.length} left)
            </button>
          )}
        </section>
      </div>
    </div>
  );
}

export default function Papers() {
  return <Suspense fallback={<p className="text-sm text-muted">Loading…</p>}><PapersInner /></Suspense>;
}
