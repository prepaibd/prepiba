"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { MathText } from "@/components/math-text";
import { UsageBadge } from "@/components/usage-badge";
import { ApiError, api, get, post } from "@/lib/api";
import { streamMessage } from "@/lib/stream";
import type { ChatMessage, ChatSessionDetail, ChatSessionSummary, Paginated, Usage } from "@/lib/types";

const SUGGESTIONS = [
  "Explain the method for this step by step.",
  "What is the common trap in a question like this?",
  "Give me a similar practice question.",
];

function TutorInner() {
  const router = useRouter();
  const params = useSearchParams();
  const sid = params.get("s");
  const questionId = params.get("q");

  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [session, setSession] = useState<ChatSessionDetail | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [streaming, setStreaming] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  const abort = useRef<AbortController | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const creating = useRef(false);
  const tempCounter = useRef(0);

  const refreshList = useCallback(() => {
    get<Paginated<ChatSessionSummary>>("/chat/sessions/", { page_size: 50 }).then((d) => setSessions(d.results)).catch(() => {});
    get<Usage>("/ai/usage/").then(setUsage).catch(() => {});
  }, []);

  useEffect(() => { refreshList(); }, [refreshList]);

  // "/chat?q=<question>" starts a chat about that question and swaps the URL to the new session.
  useEffect(() => {
    if (!questionId || creating.current) return;
    creating.current = true;
    post<ChatSessionSummary>("/chat/sessions/", { question_id: questionId })
      .then((s) => router.replace(`/chat?s=${s.id}`))
      .catch(() => { creating.current = false; setError("Could not start a chat about that question."); });
  }, [questionId, router]);

  useEffect(() => {
    if (!sid) return;
    let cancelled = false;
    get<ChatSessionDetail>(`/chat/sessions/${sid}/`)
      .then((d) => { if (!cancelled) { setSession(d); setMessages(d.messages); setError(null); refreshList(); } })
      .catch(() => { if (!cancelled) setError("Could not open that chat."); });
    return () => { cancelled = true; abort.current?.abort(); };
  }, [sid, refreshList]);

  useEffect(() => { bottom.current?.scrollIntoView({ block: "end" }); }, [messages, streaming]);

  async function newChat() {
    try {
      const s = await post<ChatSessionSummary>("/chat/sessions/", {});
      router.push(`/chat?s=${s.id}`);
    } catch { setError("Could not start a new chat."); }
  }

  async function remove(id: string) {
    await api(`/chat/sessions/${id}/`, { method: "DELETE" }).catch(() => {});
    if (id === sid) { setSession(null); setMessages([]); router.replace("/chat"); }
    refreshList();
  }

  async function send(text: string) {
    const content = text.trim();
    if (!content || !sid || streaming !== null) return;
    setError(null);
    setDraft("");
    const tempId = `tmp-${++tempCounter.current}`;
    setMessages((m) => [...m, { id: tempId, role: "user", content, created_at: "" }]);
    setStreaming("");
    abort.current = new AbortController();
    let failed = false;
    try {
      await streamMessage(sid, content, (e) => {
        if (e.type === "delta") setStreaming((s) => (s ?? "") + e.text);
        else if (e.type === "error") { failed = true; setError(e.detail); }
      }, abort.current.signal);
    } catch (e) {
      failed = true;
      if (e instanceof ApiError && e.status === 429) setError(e.message);
      else if ((e as Error).name !== "AbortError") setError("Could not reach the tutor. Please try again.");
    }
    if (failed) {
      setMessages((m) => m.filter((x) => x.id !== tempId));
      setDraft(content); // give the text back so nothing is lost
      setStreaming(null);
    } else {
      // reload so ids and saved text come from the server
      const d = await get<ChatSessionDetail>(`/chat/sessions/${sid}/`).catch(() => null);
      if (d) setMessages(d.messages);
      setStreaming(null);
    }
    refreshList();
  }

  const empty = messages.length === 0 && streaming === null;

  return (
    <div className="grid gap-6 md:grid-cols-[240px_1fr]">
      <aside className="space-y-3">
        <button className="btn btn-primary w-full" onClick={newChat}>New chat</button>
        <ul className="space-y-1">
          {sessions.map((s) => (
            <li key={s.id} className={`group flex items-center gap-1 rounded-lg ${s.id === sid ? "bg-accent-soft" : "hover:bg-surface-2"}`}>
              <Link href={`/chat?s=${s.id}`} className="min-w-0 flex-1 truncate px-3 py-2 text-sm">{s.title || "New chat"}</Link>
              <button aria-label={`Delete chat ${s.title}`} onClick={() => remove(s.id)}
                className="px-2 text-muted opacity-0 hover:text-bad focus:opacity-100 group-hover:opacity-100">×</button>
            </li>
          ))}
          {sessions.length === 0 && <li className="px-3 text-sm text-muted">No chats yet.</li>}
        </ul>
      </aside>

      <section className="card flex min-h-[28rem] flex-col">
        <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
          <p className="truncate text-sm font-medium">{session?.title || "Chat"}</p>
          <UsageBadge item={usage?.chat} noun="messages" />
        </div>

        {!sid && !questionId && (
          <div className="grid flex-1 place-items-center p-8 text-center text-sm text-muted">
            <p>Ask the tutor about any question or topic.<br />Start a new chat, or use “Ask AI” while reviewing a result.</p>
          </div>
        )}

        {sid && (
          <>
            {session?.question && (
              <div className="border-b border-line bg-surface-2 px-4 py-2 text-xs text-muted">
                About {session.question.exam} · Q{session.question.number}: <MathText text={session.question.stem} />
              </div>
            )}
            <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4" aria-live="polite">
              {empty && (
                <div className="space-y-2 text-sm text-muted">
                  <p>Try one of these:</p>
                  {SUGGESTIONS.map((t) => (
                    <button key={t} className="btn block w-full text-left" onClick={() => send(t)}>{t}</button>
                  ))}
                </div>
              )}
              {messages.map((m) => (
                <div key={m.id} className={m.role === "user" ? "flex justify-end" : "flex"}>
                  <div className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm ${m.role === "user" ? "bg-accent text-accent-fg" : "bg-surface-2"}`}>
                    <MathText text={m.content} markdown={m.role === "assistant"} strict />
                  </div>
                </div>
              ))}
              {streaming !== null && (
                <div className="flex">
                  <div className="max-w-[85%] rounded-2xl bg-surface-2 px-4 py-2 text-sm">
                    {streaming ? <MathText text={streaming} markdown /> : <span className="text-muted">Thinking…</span>}
                  </div>
                </div>
              )}
              <div ref={bottom} />
            </div>
            {error && <p role="alert" className="px-4 pb-2 text-sm text-bad">{error}</p>}
            <form className="flex gap-2 border-t border-line p-3" onSubmit={(e) => { e.preventDefault(); send(draft); }}>
              <textarea className="input min-h-[2.5rem] resize-y" rows={2} maxLength={2000} value={draft}
                placeholder="Ask a question…" aria-label="Message" disabled={streaming !== null}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(draft); } }} />
              <button className="btn btn-primary self-end" type="submit" disabled={streaming !== null || !draft.trim()}>Send</button>
            </form>
          </>
        )}
        {!sid && error && <p role="alert" className="px-4 pb-4 text-sm text-bad">{error}</p>}
      </section>
    </div>
  );
}

export default function Tutor() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="h1">Chat</h1>
        <p className="text-muted">Ask for explanations and methods. During a timed exam the tutor only gives hints.</p>
      </div>
      <Suspense fallback={<p className="text-sm text-muted">Loading…</p>}><TutorInner /></Suspense>
    </div>
  );
}
