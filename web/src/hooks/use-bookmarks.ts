"use client";

import { useCallback, useEffect, useState } from "react";
import { api, get } from "@/lib/api";
import type { Bookmark, Paginated } from "@/lib/types";

/** The set of bookmarked question ids, with an optimistic toggle. */
export function useBookmarks() {
  const [ids, setIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    get<Paginated<Bookmark>>("/bookmarks/", { page_size: 200 })
      .then((d) => setIds(new Set(d.results.map((b) => b.question.id))))
      .catch(() => { /* bookmarks are optional: the page works without them */ });
  }, []);

  const toggle = useCallback(async (questionId: string) => {
    const had = ids.has(questionId);
    const apply = (add: boolean) =>
      setIds((s) => { const n = new Set(s); if (add) n.add(questionId); else n.delete(questionId); return n; });
    apply(!had);
    try {
      if (had) await api(`/bookmarks/${questionId}/`, { method: "DELETE" });
      else await api("/bookmarks/", { method: "POST", body: { question_id: questionId } });
    } catch {
      apply(had); // roll back
    }
  }, [ids]);

  return { ids, toggle };
}
