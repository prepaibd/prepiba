"use client";

import Link from "next/link";
import { notFound, useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { MathText } from "@/components/math-text";
import { useLang } from "@/hooks/use-lang";
import { get } from "@/lib/api";
import { STUDY_SECTIONS } from "@/lib/study";
import type { Formula } from "@/lib/types";

export default function StudySection() {
  const { section } = useParams<{ section: string }>();
  const def = STUDY_SECTIONS.find((s) => s.slug === section);
  if (!def) notFound();
  return <SectionBody def={def} />;
}

function SectionBody({ def }: { def: (typeof STUDY_SECTIONS)[number] }) {
  const { lang } = useLang();
  const [items, setItems] = useState<Formula[] | null>(null);
  const [q, setQ] = useState("");
  const [error, setError] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset when switching sections
    setItems(null); setError(false);
    get<Formula[]>(def.endpoint).then(setItems).catch(() => setError(true));
  }, [def.endpoint]);

  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return needle ? (items ?? []).filter((i) => `${i.title} ${i.body} ${i.title_bn}`.toLowerCase().includes(needle)) : items ?? [];
  }, [items, q]);

  return (
    <div className="space-y-6">
      <div>
        <Link href="/study" className="text-sm text-muted hover:text-ink">← Study</Link>
        <h1 className="h1 mt-1">{lang === "bn" ? def.titleBn : def.title}</h1>
        <p className="text-muted">{def.blurb}</p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <input className="input max-w-xs" type="search" placeholder="Search…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search" />
        <Link href={`/practice?subject=${def.subject}`} className="btn">Practise this subject</Link>
      </div>
      {error && <p role="alert" className="text-sm text-bad">Could not load content.</p>}
      {items === null && !error && <p className="text-sm text-muted">Loading…</p>}
      {items && shown.length === 0 && <p className="text-sm text-muted">Nothing matches “{q}”.</p>}
      <div className="grid gap-3 sm:grid-cols-2">
        {shown.map((i) => (
          <article key={i.slug} className="card space-y-2 p-4">
            <h2 className="font-medium">{lang === "bn" && i.title_bn ? i.title_bn : i.title}</h2>
            <p className="text-sm text-muted"><MathText text={lang === "bn" && i.body_bn ? i.body_bn : i.body} /></p>
          </article>
        ))}
      </div>
    </div>
  );
}
