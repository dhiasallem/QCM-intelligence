"use client";

import React, { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function ExamRoomPage() {
  const params = useParams();
  const attemptId = parseInt(params.id as string);
  const router = useRouter();

  const [attemptData, setAttemptData] = useState<any | null>(null);
  const [currentQIndex, setCurrentQIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, number[]>>({});
  const [remainingSec, setRemainingSec] = useState<number | null>(null);
  const [lastSaved, setLastSaved] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showConfirmSubmit, setShowConfirmSubmit] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const answersRef = useRef(answers);
  answersRef.current = answers;

  // 1. Initialiser l'examen
  useEffect(() => {
    async function initExam() {
      try {
        const data = await api.attempts.getOrStart(attemptId);
        setAttemptData(data);
        setAnswers(data.saved_answers || {});
        setRemainingSec(data.remaining_seconds);
      } catch (err: any) {
        setError(err.message || "Impossible de charger cet examen");
      }
    }
    initExam();
  }, [attemptId]);

  // 2. Compte à rebours du minuteur
  useEffect(() => {
    if (remainingSec === null || remainingSec <= 0) return;

    const timer = setInterval(() => {
      setRemainingSec((prev) => {
        if (prev === null || prev <= 1) {
          clearInterval(timer);
          handleAutoSubmit();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [remainingSec]);

  // 3. Sauvegarde automatique périodique toutes les 20 secondes
  const triggerSave = useCallback(async () => {
    if (isSaving || !attemptData) return;
    setIsSaving(true);
    try {
      const res = await api.attempts.saveAnswers(attemptId, answersRef.current);
      setLastSaved(new Date().toLocaleTimeString("fr-FR"));
    } catch (err) {
      console.error("Autosave error", err);
    } finally {
      setIsSaving(false);
    }
  }, [attemptId, attemptData, isSaving]);

  useEffect(() => {
    const autoSaveInterval = setInterval(() => {
      triggerSave();
    }, 20000); // 20s

    return () => clearInterval(autoSaveInterval);
  }, [triggerSave]);

  const handleToggleOption = (questionId: number, optionId: number, isMultiple: boolean) => {
    setAnswers((prev) => {
      const currentSelected = prev[questionId] || [];
      let nextSelected: number[];

      if (isMultiple) {
        if (currentSelected.includes(optionId)) {
          nextSelected = currentSelected.filter((id) => id !== optionId);
        } else {
          nextSelected = [...currentSelected, optionId];
        }
      } else {
        nextSelected = [optionId];
      }

      return {
        ...prev,
        [questionId]: nextSelected,
      };
    });
  };

  const handleAutoSubmit = async () => {
    try {
      await api.attempts.submit(attemptId);
      alert("Le temps imparti est écoulé. Votre copie a été soumise automatiquement.");
      router.push(`/student/exam/${attemptId}/review`);
    } catch {
      router.push("/student");
    }
  };

  const handleManualSubmit = async () => {
    setIsSubmitting(true);
    try {
      await triggerSave(); // Sauvegarde finale des réponses
      await api.attempts.submit(attemptId);
      router.push(`/student/exam/${attemptId}/review`);
    } catch (err: any) {
      setError(err.message || "Erreur lors de la soumission de votre copie");
      setIsSubmitting(false);
    }
  };

  if (error) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-8 text-center text-red-800">
        <h2 className="text-xl font-bold">Accès non autorisé ou examen terminé</h2>
        <p className="mt-2 text-sm">{error}</p>
        <a href="/student" className="mt-5 inline-block rounded-xl bg-red-600 px-4 py-2 text-sm font-bold text-white">
          Retour à l'espace étudiant
        </a>
      </div>
    );
  }

  if (!attemptData) {
    return <div className="py-16 text-center text-slate-500">Chargement sécurisé de votre copie...</div>;
  }

  const questions = attemptData.questions || [];
  const currentQuestion = questions[currentQIndex];
  const isFirst = currentQIndex === 0;
  const isLast = currentQIndex === questions.length - 1;

  const formatTimer = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const isLowTime = remainingSec !== null && remainingSec < 300; // < 5 mins

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Top Floating Bar: Exam Subject + Countdown + Autosave Status */}
      <div className="sticky top-20 z-20 flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-4 sm:px-6 shadow-md">
        <div>
          <span className="text-xs font-bold text-indigo-600 uppercase tracking-wider">
            Épreuve en ligne
          </span>
          <h1 className="text-lg font-bold text-slate-900">{attemptData.quiz_subject}</h1>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right hidden sm:block">
            <span className="text-xs text-slate-400 font-medium">
              {isSaving ? "Sauvegarde en cours..." : lastSaved ? `Sauvegardé à ${lastSaved}` : "Sauvegarde auto activée"}
            </span>
          </div>

          <div
            className={`flex items-center gap-2 rounded-xl px-4 py-2 font-mono font-extrabold text-base border ${
              isLowTime
                ? "bg-red-50 text-red-700 border-red-300 animate-pulse"
                : "bg-slate-50 text-slate-800 border-slate-200"
            }`}
          >
            <span>⏱️</span>
            <span>{remainingSec !== null ? formatTimer(remainingSec) : "--:--"}</span>
          </div>

          <button
            onClick={() => setShowConfirmSubmit(true)}
            className="rounded-xl bg-emerald-600 px-4 py-2 text-xs font-bold text-white shadow hover:bg-emerald-700 transition"
          >
            Terminer l'examen
          </button>
        </div>
      </div>

      {/* Navigation Pills 1..N */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm flex items-center gap-2 flex-wrap">
        <span className="text-xs font-semibold text-slate-400 mr-2">Questions :</span>
        {questions.map((q: any, idx: number) => {
          const isAnswered = answers[q.id] && answers[q.id].length > 0;
          const isCurrent = idx === currentQIndex;

          return (
            <button
              key={q.id}
              onClick={() => setCurrentQIndex(idx)}
              className={`flex h-8 w-8 items-center justify-center rounded-lg text-xs font-bold transition ${
                isCurrent
                  ? "bg-indigo-600 text-white ring-2 ring-indigo-300"
                  : isAnswered
                  ? "bg-indigo-100 text-indigo-800 border border-indigo-200"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {idx + 1}
            </button>
          );
        })}
      </div>

      {/* Current Question Card */}
      {currentQuestion && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-8 shadow-sm space-y-6">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Question {currentQIndex + 1} sur {questions.length}
            </span>
            <span className="text-xs font-semibold text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full">
              {currentQuestion.is_multiple_choice ? "Plusieurs réponses possibles" : "Choix unique"}
            </span>
          </div>

          <p className="text-lg font-semibold text-slate-900 leading-relaxed">
            {currentQuestion.statement}
          </p>

          {/* Options */}
          <div className="space-y-3 pt-2">
            {currentQuestion.options.map((opt: any) => {
              const selected = (answers[currentQuestion.id] || []).includes(opt.id);

              return (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => handleToggleOption(currentQuestion.id, opt.id, currentQuestion.is_multiple_choice)}
                  className={`w-full text-left p-4 rounded-xl border-2 transition flex items-start gap-3.5 ${
                    selected
                      ? "border-indigo-600 bg-indigo-50/70 text-slate-900 shadow-sm"
                      : "border-slate-200 bg-slate-50/50 hover:bg-slate-100 text-slate-700"
                  }`}
                >
                  <div
                    className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center border transition ${
                      currentQuestion.is_multiple_choice ? "rounded-md" : "rounded-full"
                    } ${selected ? "border-indigo-600 bg-indigo-600 text-white" : "border-slate-300 bg-white"}`}
                  >
                    {selected && (
                      <span className="text-xs font-black">{currentQuestion.is_multiple_choice ? "✓" : "•"}</span>
                    )}
                  </div>
                  <span className="text-sm font-medium">{opt.text}</span>
                </button>
              );
            })}
          </div>

          {/* Stepper Buttons */}
          <div className="flex items-center justify-between pt-6 border-t border-slate-100">
            <button
              onClick={() => setCurrentQIndex((prev) => Math.max(0, prev - 1))}
              disabled={isFirst}
              className="rounded-xl border border-slate-200 px-5 py-2.5 text-xs font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-40 transition"
            >
              ← Précédente
            </button>

            {isLast ? (
              <button
                onClick={() => setShowConfirmSubmit(true)}
                className="rounded-xl bg-emerald-600 px-6 py-2.5 text-xs font-bold text-white shadow hover:bg-emerald-700 transition"
              >
                Vérifier et Soumettre ma copie →
              </button>
            ) : (
              <button
                onClick={() => setCurrentQIndex((prev) => Math.min(questions.length - 1, prev + 1))}
                className="rounded-xl bg-indigo-600 px-6 py-2.5 text-xs font-bold text-white shadow hover:bg-indigo-700 transition"
              >
                Suivante →
              </button>
            )}
          </div>
        </div>
      )}

      {/* Confirmation Modal Submit */}
      {showConfirmSubmit && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl space-y-4">
            <h3 className="text-xl font-bold text-slate-900">Confirmer la soumission</h3>
            <p className="text-sm text-slate-600">
              Êtes-vous sûr de vouloir rendre définitivement votre copie ? Une fois soumise, vous ne pourrez plus modifier vos réponses.
            </p>

            <div className="rounded-xl bg-slate-50 p-3 text-xs text-slate-600">
              <span className="font-bold">Progression :</span>{" "}
              {Object.keys(answers).filter((k) => (answers as any)[k]?.length > 0).length} sur {questions.length} questions répondues.
            </div>

            <div className="flex justify-end gap-3 pt-3">
              <button
                type="button"
                onClick={() => setShowConfirmSubmit(false)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50"
              >
                Continuer l'examen
              </button>
              <button
                type="button"
                disabled={isSubmitting}
                onClick={handleManualSubmit}
                className="rounded-lg bg-emerald-600 px-5 py-2 text-xs font-bold text-white shadow hover:bg-emerald-700 disabled:opacity-50"
              >
                {isSubmitting ? "Envoi en cours..." : "Oui, soumettre la copie"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
