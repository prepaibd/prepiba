"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { get } from "@/lib/api";
import type { AttemptSummary, Paginated } from "@/lib/types";

const MODE: Record<string, string> = {
  mock_full: "Full mock", past_paper: "Past paper", sectional: "Section", topic: "Topic practice", custom: "Custom practice",
};

export default function Dashboard() {
  const { user } = useAuth();
  const [attempts, setAttempts] = useState<AttemptSummary[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    get<Paginated<AttemptSummary>>("/attempts/", { page_size: 8 })
      .then((d) => setAttempts(d.results))
      .catch(() => setError(true));
  }, []);

  const open = attempts?.filter((a) => a.status === "in_progress") ?? [];
  const done = attempts?.filter((a) => a.status !== "in_progress") ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="h1">Welcome{user?.name ? `, ${user.name.split(" ")[0]}` : ""}</h1>
        <p className="text-muted">Pick up where you left off, or start something new.</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <Link href="/papers" className="card p-4 hover:bg-surface-2">
          <p className="font-medium">Past papers</p>
          <p className="text-sm text-muted">Browse every real IBA question, by exam or topic.</p>
        </Link>
        <Link href="/practice" className="card p-4 hover:bg-surface-2">
          <p className="font-medium">Practice</p>
          <p className="text-sm text-muted">Drill a topic, or sit a timed full-paper mock.</p>
        </Link>
        <Link href="/study" className="card p-4 hover:bg-surface-2">
          <p className="font-medium">Study</p>
          <p className="text-sm text-muted">Quick reference cards for maths and grammar.</p>
        </Link>
      </div>

      {error && <p role="alert" className="text-sm text-bad">Could not load your attempts.</p>}

      {open.length > 0 && (
        <section className="space-y-2">
          <h2 className="h2">In progress</h2>
          {open.map((a) => (
            <Link key={a.id} href={`/attempt/${a.id}`} className="card flex items-center justify-between p-4 hover:bg-surface-2">
              <span>{MODE[a.mode] ?? a.mode}{a.exam ? ` · ${a.exam.session}` : ""}</span>
              <span className="text-sm font-medium text-accent">Resume →</span>
            </Link>
          ))}
        </section>
      )}

      <section className="space-y-2">
        <h2 className="h2">Recent results</h2>
        {attempts === null && !error && <p className="text-sm text-muted">Loading…</p>}
        {attempts !== null && done.length === 0 && <p className="text-sm text-muted">No finished attempts yet.</p>}
        {done.map((a) => (
          <Link key={a.id} href={`/results/${a.id}`} className="card flex items-center justify-between p-4 hover:bg-surface-2">
            <span>
              {MODE[a.mode] ?? a.mode}{a.exam ? ` · ${a.exam.session}` : ""}
              <span className="ml-2 text-xs text-muted">{new Date(a.submitted_at ?? a.started_at).toLocaleDateString()}</span>
            </span>
            <span className="text-sm tabular-nums">{a.score} / {a.max_score}</span>
          </Link>
        ))}
      </section>
    </div>
  );
}
