"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { useLang } from "@/hooks/use-lang";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/study", label: "Study" },
  { href: "/papers", label: "Past papers" },
  { href: "/analytics", label: "Analytics" },
  { href: "/chat", label: "Chat" },
  { href: "/practice", label: "Practice" },
  { href: "/bookmarks", label: "Bookmarks" },
];

function ProfileMenu() {
  const { user, logout } = useAuth();
  const { lang, setLang } = useLang();
  const router = useRouter();
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const close = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);
  useEffect(() => setOpen(false), [path]); // eslint-disable-line react-hooks/set-state-in-effect -- close on navigation

  if (!user) return null;
  const initial = (user.name || user.email).charAt(0).toUpperCase();
  const item = "block w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-surface-2";

  return (
    <div className="relative shrink-0" ref={ref}>
      <button onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-haspopup="menu"
        className="flex items-center gap-2 rounded-xl p-1 pr-2 hover:bg-surface-2">
        <span className="grid h-8 w-8 place-items-center overflow-hidden rounded-full bg-accent text-sm font-semibold text-accent-fg">
          {user.avatar_url
            // eslint-disable-next-line @next/next/no-img-element
            ? <img src={user.avatar_url} alt="" referrerPolicy="no-referrer" className="h-full w-full object-cover" />
            : initial}
        </span>
        <span className="hidden text-left leading-tight sm:block">
          <span className="block max-w-[120px] truncate text-xs font-semibold">{user.name || "Student"}</span>
          <span className="block text-[10px] capitalize text-muted">{user.plan} plan</span>
        </span>
        <span aria-hidden className="text-xs text-muted">▾</span>
      </button>
      {open && (
        <div role="menu" className="card absolute right-0 z-20 mt-2 w-60 space-y-1 p-1.5 shadow-xl">
          <div className="border-b border-line px-3 py-2">
            <p className="truncate text-sm font-semibold">{user.name || "Student"}</p>
            <p className="truncate text-xs text-muted">{user.email}</p>
          </div>
          <Link role="menuitem" href="/writing" className={item}>Writing practice</Link>
          {user.role !== "student" && <Link role="menuitem" href="/review" className={item}>Review queue</Link>}
          <button role="menuitem" className={item} onClick={() => setLang(lang === "en" ? "bn" : "en")}>
            Question language: <b>{lang === "en" ? "English → বাংলা" : "বাংলা → English"}</b>
          </button>
          <button role="menuitem" className={`${item} text-bad`} onClick={() => { logout(); router.replace("/login"); }}>
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, ready } = useAuth();
  const router = useRouter();
  const path = usePathname();
  const inExam = path.startsWith("/attempt/");

  useEffect(() => {
    if (ready && !user) router.replace("/login");
  }, [ready, user, router]);

  if (!ready || !user) {
    return <div className="grid flex-1 place-items-center text-sm text-muted">Loading…</div>;
  }
  // The exam screen is distraction-free: no site navigation while a test is running.
  if (inExam) return <>{children}</>;

  return (
    <>
      <header className="sticky top-0 z-10 border-b border-line bg-surface/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3">
          <Link href="/dashboard" className="text-lg font-semibold tracking-tight">
            Prep<span className="text-accent">IBA</span>
          </Link>
          <nav className="flex flex-1 gap-1 overflow-x-auto" aria-label="Main">
            {NAV.map((n) => {
              const active = path === n.href || path.startsWith(n.href + "/");
              return (
                <Link key={n.href} href={n.href} aria-current={active ? "page" : undefined}
                  className={`whitespace-nowrap rounded-md px-3 py-1.5 text-sm ${
                    active ? "bg-accent-soft font-medium text-accent" : "text-muted hover:text-ink"}`}>
                  {n.label}
                </Link>
              );
            })}
          </nav>
          <ProfileMenu />
        </div>
      </header>
      <main className="page flex-1">{children}</main>
    </>
  );
}
