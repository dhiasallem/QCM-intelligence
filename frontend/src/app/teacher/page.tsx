"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function TeacherDashboard() {
  const [quizzes, setQuizzes] = useState<any[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [groups, setGroups] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [qList, sList, gList] = await Promise.all([
          api.quizzes.list(),
          api.sessions.list(),
          api.groups.list(),
        ]);
        setQuizzes(qList);
        setSessions(sList);
        setGroups(gList);
      } catch (err) {
        console.error("Erreur de chargement", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="py-12 text-center text-slate-500">
        Chargement des indicateurs...
      </div>
    );
  }

  const openSessionsCount = sessions.filter((s) => s.status === "OPEN").length;
  const totalSubmissions = sessions.reduce((acc, s) => acc + (s.submitted_attempts || 0), 0);

  return (
    <div className="space-y-8">
      {/* Welcome & Quick CTA */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl bg-gradient-to-r from-indigo-700 to-indigo-900 p-6 sm:p-8 text-white shadow-lg">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Espace Enseignant
          </h1>
          <p className="mt-2 text-indigo-100 text-sm sm:text-base max-w-xl">
            Créez un QCM par l'IA, validez-le et distribuez des copies individualisées à vos étudiants.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <a
            href="/teacher/quizzes/new"
            className="rounded-xl bg-white px-4 py-2.5 text-sm font-bold text-indigo-700 shadow hover:bg-indigo-50 transition"
          >
            + Générer un QCM IA
          </a>
          <a
            href="/teacher/sessions"
            className="rounded-xl bg-indigo-500/30 border border-white/20 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500/50 transition"
          >
            Créer une session
          </a>
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Banques QCM
          </p>
          <p className="mt-2 text-3xl font-bold text-slate-900">{quizzes.length}</p>
          <p className="mt-1 text-xs text-slate-500">
            {quizzes.filter((q) => q.status === "VALIDATED").length} validées
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Sessions Ouvertes
          </p>
          <p className="mt-2 text-3xl font-bold text-indigo-600">{openSessionsCount}</p>
          <p className="mt-1 text-xs text-slate-500">Examens en cours</p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Copies Remises
          </p>
          <p className="mt-2 text-3xl font-bold text-emerald-600">{totalSubmissions}</p>
          <p className="mt-1 text-xs text-slate-500">Prêtes à être corrigées</p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Groupes d'étudiants
          </p>
          <p className="mt-2 text-3xl font-bold text-slate-900">{groups.length}</p>
          <p className="mt-1 text-xs text-slate-500">Classes enregistrées</p>
        </div>
      </div>

      {/* Recent Sessions & Quizzes */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Quizzes */}
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-100 p-5">
            <h2 className="font-bold text-slate-900 text-lg">Dernières banques de QCM</h2>
            <a href="/teacher/quizzes" className="text-xs font-semibold text-indigo-600 hover:text-indigo-800">
              Voir tout →
            </a>
          </div>
          <div className="divide-y divide-slate-100">
            {quizzes.length === 0 ? (
              <p className="p-6 text-sm text-slate-500 text-center">Aucun QCM créé pour l'instant.</p>
            ) : (
              quizzes.slice(0, 5).map((q) => (
                <div key={q.id} className="p-4 flex items-center justify-between hover:bg-slate-50 transition">
                  <div>
                    <a href={`/teacher/quizzes/${q.id}`} className="font-semibold text-slate-800 hover:text-indigo-600 text-sm">
                      {q.subject}
                    </a>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {q.specialty} • Niveau {q.level} • {q.nb_questions} questions requises
                    </p>
                  </div>
                  <div>
                    <span
                      className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${
                        q.status === "VALIDATED"
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          : q.status === "GENERATING"
                          ? "bg-amber-50 text-amber-700 border border-amber-200 animate-pulse"
                          : "bg-slate-100 text-slate-700 border border-slate-200"
                      }`}
                    >
                      {q.status}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Recent Exam Sessions */}
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-100 p-5">
            <h2 className="font-bold text-slate-900 text-lg">Sessions d'examen récentes</h2>
            <a href="/teacher/sessions" className="text-xs font-semibold text-indigo-600 hover:text-indigo-800">
              Voir tout →
            </a>
          </div>
          <div className="divide-y divide-slate-100">
            {sessions.length === 0 ? (
              <p className="p-6 text-sm text-slate-500 text-center">Aucune session d'examen configurée.</p>
            ) : (
              sessions.slice(0, 5).map((s) => (
                <div key={s.id} className="p-4 flex items-center justify-between hover:bg-slate-50 transition">
                  <div>
                    <a href={`/teacher/sessions/${s.id}`} className="font-semibold text-slate-800 hover:text-indigo-600 text-sm">
                      {s.quiz_subject || "Examen"}
                    </a>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Groupe : {s.group_name || "N/A"} • Durée {s.duration_minutes} min • {s.submitted_attempts}/{s.total_attempts} copies remises
                    </p>
                  </div>
                  <span
                    className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${
                      s.status === "OPEN"
                        ? "bg-indigo-50 text-indigo-700 border border-indigo-200"
                        : s.status === "CLOSED"
                        ? "bg-slate-100 text-slate-600"
                        : "bg-amber-50 text-amber-700 border border-amber-200"
                    }`}
                  >
                    {s.status}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
