"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, ApiError, tokens } from "@/lib/api";
import type { User } from "@/lib/types";

interface AuthState {
  user: User | null;
  ready: boolean; // false until the stored session has been checked
  setUser: (u: User | null) => void;
  logout: () => void;
}

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (tokens.has()) {
        try {
          const me = await api<User>("/auth/me/");
          if (!cancelled) setUser(me);
        } catch (e) {
          if (!(e instanceof ApiError)) console.error(e); // network error: keep the tokens
        }
      }
      if (!cancelled) setReady(true);
    })();
    return () => { cancelled = true; };
  }, []);

  const logout = useCallback(() => { tokens.clear(); setUser(null); }, []);
  return <Ctx.Provider value={{ user, ready, setUser, logout }}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
