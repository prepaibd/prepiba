"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useLang } from "@/hooks/use-lang";
import { get } from "@/lib/api";
import { STUDY_SECTIONS } from "@/lib/study";

export default function Study() {
  const { lang } = useLang();
  const [counts, setCounts] = useState<Record<string, number>>({});

  useEffect(() => {
    STUDY_SECTIONS.forEach((s) =>
      get<unknown[]>(s.endpoint).then((d) => setCounts((c) => ({ ...c, [s.slug]: d.length }))).catch(() => {}));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="h1">Study</h1>
        <p className="text-muted">Learn the ideas first, then test them in Practice and Past papers.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {STUDY_SECTIONS.map((s) => (
          <Link key={s.slug} href={`/study/${s.slug}`}
            className="card group flex flex-col justify-between gap-6 p-6 transition hover:-translate-y-0.5 hover:shadow-md">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-4">
                <span className="grid h-12 w-12 place-items-center rounded-xl bg-accent-soft text-lg font-semibold text-accent">{s.icon}</span>
                <div>
                  <h2 className="text-lg font-semibold group-hover:text-accent">{lang === "bn" ? s.titleBn : s.title}</h2>
                  <p className="text-xs text-muted">{lang === "bn" ? s.title : s.titleBn}</p>
                </div>
              </div>
              <span aria-hidden className="rounded-lg bg-surface-2 px-2 py-1 text-muted group-hover:text-accent">↗</span>
            </div>
            <p className="text-sm text-muted">{s.blurb}</p>
            <div className="border-t border-line pt-3 text-xs text-muted">
              {counts[s.slug] !== undefined ? `${counts[s.slug]} cards` : "…"}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
