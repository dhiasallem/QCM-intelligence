"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function NewQuizPage() {
  const router = useRouter();
  const [specialty, setSpecialty] = useState("Informatique");
  const [subject, setSubject] = useState("Bases de données relationnelles");
  const [level, setLevel] = useState("Licence 2");
  const [nbQuestions, setNbQuestions] = useState(5);
  const [chapters, setChapters] = useState("Modèle relationnel, Algèbre relationnelle, Clés et contraintes, Requêtes SQL SELECT");

  const [loading, setLoading] = useState(false);
  const [generatingQuizId, setGeneratingQuizId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const created = await api.quizzes.create({
        specialty,
        subject,
        level,
        nb_questions: nbQuestions,
        chapters: chapters.trim() || undefined,
      });

      setGeneratingQuizId(created.id);
    } catch (err: any) {
      setError(err.message || "Erreur lors de la création de la tâche");
      setLoading(false);
    }
  };

  // Polling tant que le statut est GENERATING
  useEffect(() => {
    if (!generatingQuizId) return;

    const interval = setInterval(async () => {
      try {
        const quiz = await api.quizzes.get(generatingQuizId);
        if (quiz.status === "DRAFT" || quiz.status === "VALIDATED") {
          clearInterval(interval);
          router.push(`/teacher/quizzes/${generatingQuizId}`);
        } else if (quiz.status === "FAILED") {
          clearInterval(interval);
          setError(`La génération par IA a échoué : ${quiz.error || "Erreur inconnue"}`);
          setGeneratingQuizId(null);
          setLoading(false);
        }
      } catch (err: any) {
        console.error("Erreur polling", err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [generatingQuizId, router]);

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <a href="/teacher/quizzes" className="text-sm font-medium text-indigo-600 hover:text-indigo-800">
          ← Retour aux banques de QCM
        </a>
        <h1 className="mt-2 text-2xl font-bold text-slate-900">
          Générer une banque de questions avec l'Agent IA
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          L'agent (Gemini avec bascule Mistral) produira une banque élargie de {nbQuestions * 2} questions structurées et étiquetées que vous pourrez relire et valider.
        </p>
      </div>

      {error && (
        <div className="rounded-xl bg-red-50 p-4 border border-red-200 text-sm text-red-700">
          {error}
        </div>
      )}

      {generatingQuizId ? (
        <div className="rounded-2xl border border-indigo-100 bg-white p-10 text-center shadow-sm">
          <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-solid border-indigo-600 border-r-transparent"></div>
          <h2 className="mt-5 text-lg font-bold text-slate-800">
            L'IA est en train de concevoir vos questions...
          </h2>
          <p className="mt-2 text-sm text-slate-500 max-w-md mx-auto">
            Génération d'une banque de {nbQuestions * 2} questions (faciles, moyennes, difficiles) avec propositions plausibles et explications. Redirection automatique dès finalisation...
          </p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                Spécialité / Filière
              </label>
              <input
                type="text"
                required
                value={specialty}
                onChange={(e) => setSpecialty(e.target.value)}
                placeholder="Ex: Informatique, Gestion, Droit"
                className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100 outline-none transition"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                Niveau d'études
              </label>
              <input
                type="text"
                required
                value={level}
                onChange={(e) => setLevel(e.target.value)}
                placeholder="Ex: Licence 2, BTS, Master 1"
                className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100 outline-none transition"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-1.5">
              Matière / Intitulé du cours
            </label>
            <input
              type="text"
              required
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Ex: Bases de données relationnelles & SQL"
              className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100 outline-none transition"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-1.5">
              Nombre de questions par étudiant dans l'examen final (N)
            </label>
            <input
              type="number"
              min={1}
              max={30}
              required
              value={nbQuestions}
              onChange={(e) => setNbQuestions(parseInt(e.target.value) || 1)}
              className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100 outline-none transition"
            />
            <p className="mt-1 text-xs text-slate-400">
              💡 La banque générée comportera {nbQuestions * 2} questions pour permettre le tirage au sort stratifié.
            </p>
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-1.5">
              Chapitres ou notions clés à couvrir (optionnel)
            </label>
            <textarea
              rows={3}
              value={chapters}
              onChange={(e) => setChapters(e.target.value)}
              placeholder="Ex: Modèle relationnel, clés primaires et étrangères, jointures INNER et LEFT JOIN"
              className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100 outline-none transition"
            />
          </div>

          <div className="border-t border-slate-100 pt-6 flex justify-end gap-3">
            <button
              type="button"
              onClick={() => router.push("/teacher/quizzes")}
              className="rounded-lg border border-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-50 transition"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={loading}
              className="rounded-lg bg-indigo-600 px-6 py-2.5 text-sm font-bold text-white shadow hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 transition"
            >
              Lancer la génération IA
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
