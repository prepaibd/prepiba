"use client";

import { useRouter } from "next/navigation";
import Script from "next/script";
import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { loginWith } from "@/lib/api";

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "";
const DEV_LOGIN = process.env.NEXT_PUBLIC_DEV_LOGIN === "1";

interface GoogleId {
  initialize: (o: { client_id: string; callback: (r: { credential: string }) => void }) => void;
  renderButton: (el: HTMLElement, o: Record<string, unknown>) => void;
}
declare global {
  interface Window { google?: { accounts: { id: GoogleId } } }
}

export default function LoginPage() {
  const { user, ready, setUser } = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const buttonRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ready && user) router.replace("/dashboard");
  }, [ready, user, router]);

  const onCredential = useCallback(async (credential: string) => {
    try {
      setUser(await loginWith("/auth/google/", { id_token: credential }));
      router.replace("/dashboard");
    } catch {
      setError("Google sign-in failed. Please try again.");
    }
  }, [router, setUser]);

  const initGoogle = useCallback(() => {
    if (!CLIENT_ID || !window.google || !buttonRef.current) return;
    window.google.accounts.id.initialize({ client_id: CLIENT_ID, callback: (r) => onCredential(r.credential) });
    window.google.accounts.id.renderButton(buttonRef.current, { theme: "outline", size: "large", width: 280 });
  }, [onCredential]);

  useEffect(() => { initGoogle(); }, [initGoogle]);

  async function devLogin(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      setUser(await loginWith("/auth/dev-login/", { email }));
      router.replace("/dashboard");
    } catch {
      setError("Dev login failed. Is the API running with DEV_LOGIN_ENABLED?");
    }
  }

  return (
    <main className="grid flex-1 place-items-center px-4 py-12">
      <div className="card w-full max-w-sm space-y-6 p-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Prep<span className="text-accent">IBA</span></h1>
          <p className="mt-1 text-sm text-muted">Practice real IBA MBA admission papers, with worked solutions.</p>
        </div>
        {CLIENT_ID ? (
          <>
            <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" onReady={initGoogle} />
            <div ref={buttonRef} />
          </>
        ) : (
          !DEV_LOGIN && <p className="text-sm text-warn">Google sign-in is not configured.</p>
        )}
        {DEV_LOGIN && (
          <form onSubmit={devLogin} className="space-y-3 border-t border-line pt-4">
            <p className="text-xs font-medium uppercase tracking-wide text-muted">Development login</p>
            <input className="input" type="email" required placeholder="you@example.com" value={email}
              onChange={(e) => setEmail(e.target.value)} aria-label="Email" />
            <button className="btn btn-primary w-full" type="submit">Continue</button>
          </form>
        )}
        {error && <p role="alert" className="text-sm text-bad">{error}</p>}
      </div>
    </main>
  );
}
