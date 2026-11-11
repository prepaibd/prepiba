"use client";

import { createContext, useCallback, useContext, useSyncExternalStore, type ReactNode } from "react";
import type { Lang } from "@/lib/types";

const KEY = "prepiba:lang";
const listeners = new Set<() => void>();

function read(): Lang {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === "bn" || saved === "en") return saved;
  } catch { /* storage unavailable */ }
  return "en";
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  window.addEventListener("storage", cb);
  return () => { listeners.delete(cb); window.removeEventListener("storage", cb); };
}

const Ctx = createContext<{ lang: Lang; setLang: (l: Lang) => void }>({ lang: "en", setLang: () => {} });

export function LangProvider({ children }: { children: ReactNode }) {
  // Server and first client render use "en"; the stored choice is applied right after hydration.
  const lang = useSyncExternalStore(subscribe, read, () => "en" as Lang);
  const setLang = useCallback((l: Lang) => {
    try { localStorage.setItem(KEY, l); } catch { /* ignore */ }
    listeners.forEach((cb) => cb());
  }, []);
  return <Ctx.Provider value={{ lang, setLang }}>{children}</Ctx.Provider>;
}

export const useLang = () => useContext(Ctx);
