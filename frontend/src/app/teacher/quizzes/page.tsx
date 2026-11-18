"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function QuizzesListPage() {
  const [quizzes, setQuizzes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleDelete = async (q: any) => {
    if (!confirm(`Supprimer définitivement la banque "${q.subject}" et toutes ses questions ?`)) return;
    setError(null);
    try {
      await api.quizzes.delete(q.id);
      setQuizzes((prev) => prev.filter((x) => x.id !== q.id));
    } catch (err: any) {
      setError(err.message || "Erreur lors de la suppression");
    }
  };

  const loadQuizzes = async () => {
    try {
      const data = await api.quizzes.list();
      setQuizzes(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQuizzes();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Banques de questions (QCM)</h1>
          <p className="text-sm text-slate-500 mt-1">
            Chaque banque est générée par l'IA puis validée par vous avant d'être proposée en examen.
          </p>
        </div>
        <a
          href="/teacher/quizzes/new"
          className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-bold text-white shadow hover:bg-indigo-700 transition inline-block text-center"
        >
          + Nouvelle génération IA
        </a>
      </div>

      {error && (
        <div className="rounded-xl bg-red-50 p-4 border border-red-200 text-sm text-red-700">{error}</div>
      )}

      {loading ? (
        <div className="py-12 text-center text-slate-500">Chargement des QCM...</div>
      ) : quizzes.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center">
          <p className="text-base font-medium text-slate-700">Vous n'avez pas encore de banque de QCM.</p>
          <p className="mt-1 text-sm text-slate-400">
            Cliquez sur "Nouvelle génération IA" pour créer votre premier examen en quelques secondes.
          </p>
          <a
            href="/teacher/quizzes/new"
            className="mt-5 inline-block rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-indigo-700 transition"
          >
            Créer avec l'IA
          </a>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {quizzes.map((q) => (
            <div
              key={q.id}
              className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm hover:shadow-md transition flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-3">
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-600">
                    {q.specialty}
                  </span>
                  <span
                    className={`text-xs font-bold px-2.5 py-1 rounded-full ${
                      q.status === "VALIDATED"
                        ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                        : q.status === "GENERATING"
                        ? "bg-amber-50 text-amber-700 border border-amber-200 animate-pulse"
                        : q.status === "FAILED"
                        ? "bg-red-50 text-red-700 border border-red-200"
                        : "bg-blue-50 text-blue-700 border border-blue-200"
                    }`}
                  >
                    {q.status === "VALIDATED"
                      ? "Prêt pour examen"
                      : q.status === "DRAFT"
                      ? "À relire"
                      : q.status}
                  </span>
                </div>

                <h2 className="text-lg font-bold text-slate-900 line-clamp-2">{q.subject}</h2>
                <p className="text-xs text-slate-500 mt-1">Niveau : {q.level}</p>

                <div className="mt-4 rounded-xl bg-slate-50 p-3 text-xs text-slate-600 space-y-1">
                  <p>
                    <span className="font-semibold text-slate-800">Tirage par copie :</span> {q.nb_questions} questions
                  </p>
                  <p>
                    <span className="font-semibold text-slate-800">Fournisseur :</span> {q.provider || "Gemini / Mistral"}
                  </p>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between">
                <span className="text-xs text-slate-400">
                  {new Date(q.created_at).toLocaleDateString("fr-FR")}
                </span>
                <div className="flex items-center gap-3">
                  {q.status !== "GENERATING" && (
                    <button
                      onClick={() => handleDelete(q)}
                      className="text-xs font-semibold text-red-600 hover:text-red-800 transition"
                    >
                      Supprimer
                    </button>
                  )}
                  <a
                    href={`/teacher/quizzes/${q.id}`}
                    className="rounded-lg bg-indigo-50 px-3.5 py-1.5 text-xs font-bold text-indigo-700 hover:bg-indigo-100 transition"
                  >
                    {q.status === "VALIDATED" ? "Voir les questions →" : "Relire & Valider →"}
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
