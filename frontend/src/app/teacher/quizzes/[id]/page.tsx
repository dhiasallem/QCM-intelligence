"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function QuizDetailPage() {
  const params = useParams();
  const quizId = parseInt(params.id as string);
  const router = useRouter();

  const [quiz, setQuiz] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [validating, setValidating] = useState(false);
  const [editingQuestionId, setEditingQuestionId] = useState<number | null>(null);
  const [filterDifficulty, setFilterDifficulty] = useState<string>("all");

  const loadQuiz = async () => {
    try {
      const data = await api.quizzes.get(quizId);
      setQuiz(data);
    } catch (err: any) {
      setError(err.message || "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQuiz();
  }, [quizId]);

  const handleValidate = async () => {
    setError(null);
    setValidating(true);
    try {
      await api.quizzes.validate(quizId);
      await loadQuiz();
    } catch (err: any) {
      setError(err.message || "Impossible de valider ce QCM");
    } finally {
      setValidating(false);
    }
  };

  const handleRetryGeneration = async () => {
    setError(null);
    setValidating(true);
    try {
      await api.quizzes.retry(quizId);
      await loadQuiz();
    } catch (err: any) {
      setError(err.message || "Impossible de relancer la génération");
    } finally {
      setValidating(false);
    }
  };

  const handleDeleteQuestion = async (qId: number) => {
    if (!confirm("Voulez-vous vraiment supprimer cette question de la banque ?")) return;
    try {
      await api.questions.delete(qId);
      await loadQuiz();
    } catch (err: any) {
      setError(err.message || "Erreur lors de la suppression");
    }
  };

  const handleDeleteQuiz = async () => {
    if (!confirm("Supprimer définitivement cette banque et toutes ses questions ?")) return;
    setError(null);
    try {
      await api.quizzes.delete(quizId);
      router.push("/teacher/quizzes");
    } catch (err: any) {
      setError(err.message || "Erreur lors de la suppression");
    }
  };

  if (loading) return <div className="py-12 text-center text-slate-500">Chargement de la banque...</div>;
  if (!quiz) return <div className="py-12 text-center text-red-500">{error || "QCM introuvable"}</div>;

  const questions = quiz.questions || [];
  const filteredQuestions = filterDifficulty === "all"
    ? questions
    : questions.filter((q: any) => q.difficulty === filterDifficulty);

  const isValidated = quiz.status === "VALIDATED";

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Top Breadcrumb & Summary */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <a href="/teacher/quizzes" className="text-xs font-semibold text-indigo-600 hover:text-indigo-800">
            ← Retour à toutes les banques
          </a>
          <div className="flex items-center gap-3 mt-1">
            <h1 className="text-2xl font-black text-slate-900">{quiz.subject}</h1>
            <span
              className={`text-xs font-bold px-2.5 py-1 rounded-full ${
                isValidated
                  ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                  : "bg-amber-50 text-amber-700 border border-amber-200"
              }`}
            >
              {isValidated ? "✓ Validé pour session" : "Brouillon (À valider)"}
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            {quiz.specialty} • Niveau {quiz.level} • Tirage de {quiz.nb_questions} questions par copie
          </p>
        </div>

        <div className="flex items-center gap-3">
          {quiz.status !== "GENERATING" && (
            <button
              onClick={handleDeleteQuiz}
              className="rounded-xl border border-red-200 bg-white px-4 py-2.5 text-sm font-bold text-red-600 hover:bg-red-50 transition"
            >
              Supprimer la banque
            </button>
          )}
          {isValidated ? (
            <a
              href={`/teacher/sessions?new_for_quiz=${quiz.id}`}
              className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-bold text-white shadow hover:bg-indigo-700 transition"
            >
              Planifier un examen avec ce QCM →
            </a>
          ) : quiz.status === "FAILED" ? (
            <button
              onClick={handleRetryGeneration}
              disabled={validating}
              className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-bold text-white shadow hover:bg-indigo-700 disabled:opacity-50 transition"
            >
              {validating ? "Relance en cours..." : "🔄 Relancer la génération"}
            </button>
          ) : (
            <button
              onClick={handleValidate}
              disabled={validating || questions.length < quiz.nb_questions}
              className="rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-bold text-white shadow hover:bg-emerald-700 disabled:opacity-50 transition"
            >
              {validating ? "Validation..." : "Valider la banque de questions"}
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-xl bg-red-50 p-4 border border-red-200 text-sm text-red-700">
          {error}
        </div>
      )}

      {quiz.status === "FAILED" && (
        <div className="rounded-xl bg-red-50 p-5 border border-red-200 text-sm text-red-800 space-y-2">
          <p className="font-bold text-red-900">La génération par l'IA a rencontré une erreur :</p>
          <p className="text-xs whitespace-pre-line break-words bg-white p-3 rounded border border-red-200 text-red-700">{quiz.error}</p>
          <button
            onClick={handleRetryGeneration}
            disabled={validating}
            className="mt-2 rounded-lg bg-red-600 px-4 py-2 text-xs font-bold text-white hover:bg-red-700 disabled:opacity-50"
          >
            {validating ? "Nouvel essai en cours..." : "Réessayer la génération maintenant"}
          </button>
        </div>
      )}

      {/* Info Notice about Validation */}
      {!isValidated && quiz.status !== "FAILED" && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 flex items-start gap-3">
          <span className="text-lg">⚠️</span>
          <div>
            <p className="font-semibold">Revue humaine requise</p>
            <p className="text-xs mt-0.5 text-amber-700">
              Conformément aux exigences pédagogiques, vous devez vérifier les propositions générées par l'IA. Vous pouvez modifier ou supprimer les questions avant de valider la banque.
              Actuellement {questions.length} questions dans la banque (minimum requis : {quiz.nb_questions}).
            </p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-500">Filtrer par difficulté :</span>
          {["all", "facile", "moyen", "difficile"].map((diff) => (
            <button
              key={diff}
              onClick={() => setFilterDifficulty(diff)}
              className={`rounded-lg px-3 py-1 text-xs font-semibold transition capitalize ${
                filterDifficulty === diff
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-200 text-slate-700 hover:bg-slate-300"
              }`}
            >
              {diff === "all" ? "Toutes" : diff}
            </button>
          ))}
        </div>
        <p className="text-xs text-slate-400 font-medium">
          {filteredQuestions.length} question(s) affichée(s)
        </p>
      </div>

      {/* Questions list */}
      <div className="space-y-5">
        {filteredQuestions.map((q: any, idx: number) => (
          <div
            key={q.id}
            className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm hover:border-slate-300 transition"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-100 text-xs font-black text-slate-700">
                  {idx + 1}
                </span>
                <span
                  className={`text-xs font-bold px-2 py-0.5 rounded capitalize ${
                    q.difficulty === "facile"
                      ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                      : q.difficulty === "moyen"
                      ? "bg-blue-50 text-blue-700 border border-blue-200"
                      : "bg-purple-50 text-purple-700 border border-purple-200"
                  }`}
                >
                  {q.difficulty}
                </span>
                {q.chapter && (
                  <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-medium">
                    📖 {q.chapter}
                  </span>
                )}
              </div>

              {!isValidated && (
                <button
                  onClick={() => handleDeleteQuestion(q.id)}
                  className="text-xs font-semibold text-red-600 hover:text-red-800 transition"
                >
                  Supprimer
                </button>
              )}
            </div>

            <p className="mt-3 text-base font-semibold text-slate-900 leading-relaxed">
              {q.statement}
            </p>

            {/* Options list */}
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
              {q.options?.map((opt: any) => (
                <div
                  key={opt.id}
                  className={`rounded-xl p-3 text-sm flex items-start gap-2.5 border transition ${
                    opt.is_correct
                      ? "bg-emerald-50 border-emerald-300 text-emerald-950 font-medium"
                      : "bg-slate-50 border-slate-200 text-slate-700"
                  }`}
                >
                  <span
                    className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                      opt.is_correct ? "bg-emerald-600 text-white" : "bg-slate-300 text-white"
                    }`}
                  >
                    {opt.is_correct ? "✓" : "•"}
                  </span>
                  <span>{opt.text}</span>
                </div>
              ))}
            </div>

            {q.explanation && (
              <div className="mt-4 rounded-xl bg-slate-50 border border-slate-100 p-3 text-xs text-slate-600">
                <span className="font-bold text-slate-700">💡 Explication :</span> {q.explanation}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
