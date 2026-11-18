"use client";

import React, { useEffect } from "react";
import Link from "next/navigation";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function TeacherLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && (!user || (user.role !== "teacher" && user.role !== "admin"))) {
      router.push("/login");
    }
  }, [user, loading, router]);

  if (loading || !user) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-slate-500">Chargement de votre espace...</p>
      </div>
    );
  }

  const navItems = [
    { label: "Vue d'ensemble", href: "/teacher" },
    { label: "Banques QCM (IA)", href: "/teacher/quizzes" },
    { label: "Sessions d'examen", href: "/teacher/sessions" },
    { label: "Groupes d'étudiants", href: "/teacher/groups" },
  ];

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Top Navbar */}
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8 h-16">
          <div className="flex items-center gap-8">
            <a href="/teacher" className="flex items-center gap-2.5 font-bold text-lg text-slate-900">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-white font-black text-xl shadow-sm">
                Q
              </span>
              <span>QCM Intelligence</span>
            </a>

            <nav className="hidden md:flex items-center gap-1">
              {navItems.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <a
                    key={item.href}
                    href={item.href}
                    className={`rounded-lg px-3.5 py-2 text-sm font-medium transition ${
                      isActive
                        ? "bg-indigo-50 text-indigo-700"
                        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                    }`}
                  >
                    {item.label}
                  </a>
                );
              })}
            </nav>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right hidden sm:block">
              <p className="text-sm font-semibold text-slate-800">{user.name}</p>
              <p className="text-xs text-indigo-600 font-medium capitalize">{user.role}</p>
            </div>
            <button
              onClick={logout}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
            >
              Déconnexion
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
}
