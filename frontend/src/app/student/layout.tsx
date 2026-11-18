"use client";

import React, { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

const NAV_ITEMS = [
  { label: "Rejoindre un groupe", href: "/student/groups" },
  { label: "Examens à passer", href: "/student" },
  { label: "Examens passés & résultats", href: "/student/results" },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/student") return pathname === "/student";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function StudentLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && (!user || user.role !== "student")) {
      router.push("/login");
    }
  }, [user, loading, router]);

  if (loading || !user) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-slate-500 font-medium">Chargement de votre espace étudiant...</p>
      </div>
    );
  }

  const navLinks = (
    <>
      {NAV_ITEMS.map((item) => {
        const active = isActive(pathname, item.href);
        return (
          <a
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={`shrink-0 whitespace-nowrap rounded-lg px-3.5 py-2 text-sm font-medium transition ${
              active
                ? "bg-indigo-50 text-indigo-700"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
            }`}
          >
            {item.label}
          </a>
        );
      })}
    </>
  );

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-6 px-4 sm:px-6 h-16">
          <div className="flex items-center gap-6 min-w-0">
            <a href="/student" className="flex shrink-0 items-center gap-2.5 font-bold text-lg text-slate-900">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white font-bold text-base shadow-sm">
                Q
              </span>
              <span className="hidden sm:inline">Espace Étudiant</span>
            </a>

            {/* Navigation (écrans larges) */}
            <nav aria-label="Navigation étudiant" className="hidden lg:flex items-center gap-1">
              {navLinks}
            </nav>
          </div>

          <div className="flex shrink-0 items-center gap-4">
            <div className="text-right hidden sm:block">
              <p className="text-sm font-semibold text-slate-800">{user.name}</p>
              <p className="text-xs text-slate-400">{user.email}</p>
            </div>
            <button
              onClick={logout}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
            >
              Déconnexion
            </button>
          </div>
        </div>

        {/* Navigation (mobile et tablette) : rangée défilante sous l'en-tête */}
        <nav
          aria-label="Navigation étudiant"
          className="lg:hidden flex gap-1 overflow-x-auto border-t border-slate-100 px-4 sm:px-6 py-2"
        >
          {navLinks}
        </nav>
      </header>

      <main className="mx-auto max-w-5xl px-4 sm:px-6 py-8">
        {children}
      </main>
    </div>
  );
}
