"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";

export default function StudentExamReviewPage() {
  const params = useParams();
  const attemptId = parseInt(params.id as string);

  const [review, setReview] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchReview() {
      try {
        const data = await api.attempts.getReview(attemptId);
        setReview(data);
      } catch (err: any) {
        setError(err.message || "Impossible de consulter cette correction");
      } finally {
        setLoading(false);
      }
    }
    fetchReview();
  }, [attemptId]);

  if (loading) return <div className="py-16 text-center text-slate-500">Chargement de votre copie corrigée...</div>;

  if (error) {
    return (
      <div className="max-w-2xl mx-auto rounded-2xl border border-amber-200 bg-amber-50 p-8 text-center text-amber-900">
        <h2 className="text-lg font-bold">Correction non disponible pour l'instant</h2>
        <p className="mt-2 text-sm">{error}</p>
        <a href="/student/results" className="mt-5 inline-block rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-bold text-white shadow">
          Retour à mes résultats
        </a>
      </div>
    );
  }

  const isGraded = review.status === "GRADED";
  const displayScore = isGraded ? review.final_score : review.auto_score;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <a href="/student/results" className="text-xs font-semibold text-indigo-600 hover:text-indigo-800">
          ← Retour à mes résultats
        </a>
        <h1 className="text-2xl font-bold text-slate-900 mt-2">
          Résultats & Correction de l'Examen
        </h1>
      </div>

      {/* Score Banner */}
      <div className="rounded-2xl border border-indigo-100 bg-gradient-to-r from-indigo-50 to-white p-6 sm:p-8 flex flex-col sm:flex-row items-center justify-between gap-6 shadow-sm">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">
            {isGraded ? "✓ Note finale validée par le professeur" : "Note automatique provisoire"}
          </span>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-4xl sm:text-5xl font-black text-slate-900">
              {displayScore !== null ? displayScore.toFixed(2) : "—"}
            </span>
            <span className="text-lg font-bold text-slate-400">/ {review.total_max_score} pts</span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Copie soumise le {new Date(review.submitted_at).toLocaleDateString("fr-FR")} à {new Date(review.submitted_at).toLocaleTimeString("fr-FR")}
          </p>
        </div>

        {review.teacher_comment && (
          <div className="w-full sm:max-w-sm rounded-xl bg-white border border-indigo-200 p-4 shadow-sm">
            <p className="text-xs font-bold text-indigo-700 uppercase tracking-wider mb-1">
              💬 Remarque de votre professeur :
            </p>
            <p className="text-xs text-slate-700 italic">"{review.teacher_comment}"</p>
          </div>
        )}
      </div>

      {/* Detailed Correction */}
      <div className="space-y-5">
        <h2 className="text-lg font-bold text-slate-900">Détail des questions</h2>

        {review.questions.map((q: any, idx: number) => {
          const isFullPoints = q.score_earned === q.max_score;
          const isZero = q.score_earned === 0;

          return (
            <div
              key={q.question_id}
              className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Question {idx + 1}
                </span>
                <span
                  className={`text-xs font-bold px-3 py-1 rounded-full ${
                    isFullPoints
                      ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                      : isZero
                      ? "bg-red-50 text-red-700 border border-red-200"
                      : "bg-amber-50 text-amber-700 border border-amber-200"
                  }`}
                >
                  {q.score_earned} / {q.max_score} pts
                </span>
              </div>

              <p className="text-base font-semibold text-slate-900">{q.statement}</p>

              <div className="space-y-2 pt-1">
                {q.options.map((opt: any) => {
                  const wasChosen = opt.was_selected;
                  const isGood = opt.is_correct;

                  return (
                    <div
                      key={opt.id}
                      className={`p-3.5 rounded-xl text-xs flex items-center justify-between border ${
                        wasChosen && isGood
                          ? "bg-emerald-50 border-emerald-300 text-emerald-950 font-bold"
                          : wasChosen && !isGood
                          ? "bg-red-50 border-red-300 text-red-950 font-semibold"
                          : isGood
                          ? "bg-emerald-50/50 border-emerald-200 text-emerald-900"
                          : "bg-slate-50 border-slate-200 text-slate-600"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <span className="font-bold">
                          {wasChosen ? "👉 Votre choix :" : "⚪"}
                        </span>
                        <span>{opt.text}</span>
                      </div>
                      <span className="font-bold text-xs">
                        {isGood ? "✓ Bonne réponse" : wasChosen ? "✗ Incorrect" : ""}
                      </span>
                    </div>
                  );
                })}
              </div>

              {q.explanation && (
                <div className="rounded-xl bg-slate-50 border border-slate-100 p-3.5 text-xs text-slate-600">
                  <span className="font-bold text-slate-800">💡 Explication :</span> {q.explanation}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
