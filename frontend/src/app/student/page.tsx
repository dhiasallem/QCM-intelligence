"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function StudentExamsToTakePage() {
  const [attempts, setAttempts] = useState<any[]>([]);
  const [hasGroups, setHasGroups] = useState(true);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.attempts.myList(), api.groups.mine()])
      .then(([aList, gList]) => {
        setAttempts(aList);
        setHasGroups(gList.length > 0);
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="py-12 text-center text-slate-500">Chargement de vos examens...</div>;
  }

  const now = new Date();
  const activeExams = attempts.filter((a) => a.can_start || a.status === "IN_PROGRESS");
  const upcomingExams = attempts.filter(
    (a) => a.status === "NOT_STARTED" && !a.can_start && new Date(a.closes_at) > now
  );

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Examens à passer</h1>
        <p className="text-sm text-slate-500 mt-1">
          Les épreuves ouvertes et à venir de vos groupes.
        </p>
      </div>

      {!hasGroups && (
        <div className="rounded-2xl border border-indigo-200 bg-indigo-50/60 p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <p className="text-sm text-slate-700">
            Vous n'êtes inscrit dans aucun groupe : rejoignez celui de votre enseignant pour recevoir ses QCM.
          </p>
          <a
            href="/student/groups"
            className="shrink-0 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-bold text-white hover:bg-indigo-700 transition text-center"
          >
            Rejoindre un groupe
          </a>
        </div>
      )}

      {/* Examens ouverts */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-slate-900">Ouverts maintenant</h2>
        {activeExams.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center text-sm text-slate-400">
            Aucun examen ouvert pour le moment.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {activeExams.map((a) => (
              <div
                key={a.attempt_id}
                className="rounded-2xl border-2 border-indigo-200 bg-white p-6 shadow-sm flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                      🟢 Examen Ouvert
                    </span>
                    <span className="text-xs text-slate-400 font-semibold">
                      Durée : {a.duration_minutes} min
                    </span>
                  </div>
                  <h3 className="text-lg font-bold text-slate-900">{a.quiz_subject}</h3>
                  {a.group_name && <p className="text-xs font-medium text-indigo-600 mt-0.5">{a.group_name}</p>}
                  <p className="text-xs text-slate-500 mt-1">
                    Disponible jusqu'au {new Date(a.closes_at).toLocaleString("fr-FR")}
                  </p>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-100">
                  <a
                    href={`/student/exam/${a.attempt_id}`}
                    className="w-full inline-block text-center rounded-xl bg-indigo-600 py-3 text-sm font-bold text-white shadow hover:bg-indigo-700 transition"
                  >
                    {a.status === "IN_PROGRESS" ? "Reprendre l'épreuve en cours →" : "Commencer l'épreuve →"}
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Examens à venir (publiés mais pas encore ouverts) */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-slate-900">À venir</h2>
        {upcomingExams.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center text-sm text-slate-400">
            Aucun examen programmé.
          </div>
        ) : (
          <div className="space-y-3">
            {upcomingExams.map((a) => (
              <div
                key={a.attempt_id}
                className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-2"
              >
                <div>
                  <h3 className="font-bold text-slate-900 text-base">{a.quiz_subject}</h3>
                  {a.group_name && <p className="text-xs font-medium text-indigo-600 mt-0.5">{a.group_name}</p>}
                </div>
                <p className="text-xs text-slate-500">
                  Ouvre le {new Date(a.opens_at).toLocaleString("fr-FR")} • {a.duration_minutes} min
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
