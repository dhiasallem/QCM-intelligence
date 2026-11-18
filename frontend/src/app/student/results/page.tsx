"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function StudentResultsPage() {
  const [attempts, setAttempts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.attempts
      .myList()
      .then(setAttempts)
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="py-12 text-center text-slate-500">Chargement de vos résultats...</div>;
  }

  const pastExams = attempts.filter((a) => a.status === "SUBMITTED" || a.status === "GRADED");
  const graded = pastExams.filter((a) => a.status === "GRADED" && a.final_score !== null && a.max_score);
  const averagePercent =
    graded.length > 0
      ? Math.round((graded.reduce((sum, a) => sum + a.final_score / a.max_score, 0) / graded.length) * 100)
      : null;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Examens passés & résultats</h1>
        <p className="text-sm text-slate-500 mt-1">
          Vos copies rendues, vos notes et la correction détaillée dès publication par l'enseignant.
        </p>
      </div>

      {pastExams.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase text-slate-400">Examens rendus</p>
            <p className="mt-1 text-2xl font-bold text-slate-900">{pastExams.length}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase text-slate-400">Notés</p>
            <p className="mt-1 text-2xl font-bold text-slate-900">{graded.length}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase text-slate-400">Moyenne</p>
            <p className="mt-1 text-2xl font-bold text-indigo-700">
              {averagePercent !== null ? `${averagePercent} %` : "—"}
            </p>
          </div>
        </div>
      )}

      {pastExams.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-400">
          Vous n'avez pas encore d'épreuve terminée.{" "}
          <a href="/student" className="font-semibold text-indigo-600 hover:text-indigo-800">
            Voir les examens à passer →
          </a>
        </div>
      ) : (
        <div className="space-y-3">
          {pastExams.map((a) => (
            <div
              key={a.attempt_id}
              className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div>
                <h3 className="font-bold text-slate-900 text-base">{a.quiz_subject}</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  {a.group_name ? `${a.group_name} • ` : ""}Clôturé le {new Date(a.closes_at).toLocaleDateString("fr-FR")}
                </p>
              </div>

              <div className="flex items-center justify-between sm:justify-end gap-6">
                <div className="sm:text-right">
                  <p className="text-xs uppercase font-semibold text-slate-400">Note</p>
                  <p className="text-lg font-black text-indigo-700">
                    {a.status === "GRADED" && a.final_score !== null
                      ? `${a.final_score.toFixed(2)} / ${a.max_score} pts`
                      : "En cours de correction"}
                  </p>
                </div>

                <a
                  href={`/student/exam/${a.attempt_id}/review`}
                  className="shrink-0 rounded-lg bg-slate-100 px-3.5 py-2 text-xs font-bold text-slate-700 hover:bg-slate-200 transition"
                >
                  Voir la copie →
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
