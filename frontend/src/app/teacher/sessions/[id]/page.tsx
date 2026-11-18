"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, getToken } from "@/lib/api";

export default function SessionGradingDashboardPage() {
  const params = useParams();
  const sessionId = parseInt(params.id as string);
  const router = useRouter();

  const [session, setSession] = useState<any | null>(null);
  const [attempts, setAttempts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAttempt, setSelectedAttempt] = useState<any | null>(null);
  const [reviewData, setReviewData] = useState<any | null>(null);
  const [editScore, setEditScore] = useState<number>(0);
  const [editComment, setEditComment] = useState<string>("");
  const [savingGrade, setSavingGrade] = useState(false);
  const [cancellingQId, setCancellingQId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadSessionData = async () => {
    try {
      const [sData, aList] = await Promise.all([
        api.sessions.get(sessionId),
        api.sessions.attempts(sessionId),
      ]);
      setSession(sData);
      setAttempts(aList);
    } catch (err: any) {
      setError(err.message || "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSessionData();
  }, [sessionId]);

  const handleOpenReview = async (attempt: any) => {
    setSelectedAttempt(attempt);
    setEditScore(attempt.final_score ?? attempt.auto_score ?? 0);
    setEditComment(attempt.teacher_comment || "");
    setError(null);
    setSuccessMsg(null);
    try {
      const fullReview = await api.attempts.getReview(attempt.id);
      setReviewData(fullReview);
    } catch (err: any) {
      setError(err.message || "Erreur lors de la récupération de la copie");
    }
  };

  const handleSaveGrade = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAttempt) return;
    setSavingGrade(true);
    setError(null);
    try {
      await api.attempts.grade(selectedAttempt.id, {
        final_score: Number(editScore),
        teacher_comment: editComment.trim() || undefined,
      });
      setSuccessMsg("Note et commentaire enregistrés avec succès !");
      await loadSessionData();
      const updated = await api.attempts.getReview(selectedAttempt.id);
      setReviewData(updated);
    } catch (err: any) {
      setError(err.message || "Erreur lors de la notation");
    } finally {
      setSavingGrade(false);
    }
  };

  const handleCancelQuestion = async (qId: number) => {
    if (!confirm("Voulez-vous vraiment annuler cette question ? Elle sera exclue du barème et les notes de tous les étudiants de la classe seront recalculées automatiquement.")) return;
    setCancellingQId(qId);
    setError(null);
    try {
      const res = await api.sessions.cancelQuestion(sessionId, qId);
      alert(res.message);
      await loadSessionData();
      if (selectedAttempt) {
        const updated = await api.attempts.getReview(selectedAttempt.id);
        setReviewData(updated);
      }
    } catch (err: any) {
      setError(err.message || "Erreur lors de l'annulation");
    } finally {
      setCancellingQId(null);
    }
  };

  const handleDeleteSession = async () => {
    const started = attempts.filter((a) => a.status !== "NOT_STARTED").length;
    const message =
      attempts.length > 0
        ? `Supprimer cette session ?\n\n⚠️ Les ${attempts.length} copie(s) seront supprimées, dont ${started} déjà commencée(s) ou rendue(s), avec leurs réponses et leurs notes. Pensez à exporter le CSV avant. Cette action est irréversible.`
        : "Supprimer cette session ?";
    if (!confirm(message)) return;
    setError(null);
    try {
      await api.sessions.delete(sessionId, started > 0);
      router.push("/teacher/sessions");
    } catch (err: any) {
      setError(err.message || "Erreur lors de la suppression");
    }
  };

  const handleDownloadCsv = () => {
    const token = getToken();
    const url = api.sessions.exportUrl(sessionId);
    fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.blob())
      .then((blob) => {
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = downloadUrl;
        a.download = `resultats_session_${sessionId}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
      })
      .catch((err) => setError("Erreur lors du téléchargement du CSV"));
  };

  if (loading) return <div className="py-12 text-center text-slate-500">Chargement de la session...</div>;
  if (!session) return <div className="py-12 text-center text-red-500">{error || "Session introuvable"}</div>;

  // Calcul des statistiques
  const submittedCopies = attempts.filter((a) => a.status === "SUBMITTED" || a.status === "GRADED");
  const gradedCopies = attempts.filter((a) => a.status === "GRADED");
  const scores = submittedCopies
    .map((a) => (a.final_score !== null ? a.final_score : a.auto_score))
    .filter((s) => s !== null && s !== undefined) as number[];

  const avgScore = scores.length > 0 ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(2) : "N/A";
  const maxScore = scores.length > 0 ? Math.max(...scores).toFixed(2) : "N/A";
  const minScore = scores.length > 0 ? Math.min(...scores).toFixed(2) : "N/A";

  return (
    <div className="space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <a href="/teacher/sessions" className="text-xs font-semibold text-indigo-600 hover:text-indigo-800">
            ← Retour à toutes les sessions
          </a>
          <h1 className="text-2xl font-black text-slate-900 mt-1">
            Tableau de bord : {session.quiz_subject}
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Groupe : {session.group_name} • Règle de notation : {session.scoring_rule}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleDownloadCsv}
            className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-xs font-bold text-slate-700 shadow-sm hover:bg-slate-50 transition flex items-center gap-2"
          >
            📥 Exporter les notes (CSV)
          </button>
          <button
            onClick={handleDeleteSession}
            className="rounded-xl border border-red-200 bg-white px-4 py-2 text-xs font-bold text-red-600 shadow-sm hover:bg-red-50 transition"
          >
            Supprimer la session
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl bg-red-50 p-4 border border-red-200 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Class Statistics KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold text-slate-400 uppercase">Taux de remise</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">
            {submittedCopies.length} / {attempts.length}
          </p>
          <p className="text-xs text-slate-500 mt-0.5">{gradedCopies.length} validées par le prof</p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold text-slate-400 uppercase">Moyenne de classe</p>
          <p className="mt-1 text-2xl font-bold text-indigo-600">{avgScore}</p>
          <p className="text-xs text-slate-500 mt-0.5">Sur {session.questions_per_student * session.points_per_question} pts</p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold text-slate-400 uppercase">Note Minimale</p>
          <p className="mt-1 text-2xl font-bold text-amber-600">{minScore}</p>
          <p className="text-xs text-slate-500 mt-0.5">Note la plus basse</p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold text-slate-400 uppercase">Note Maximale</p>
          <p className="mt-1 text-2xl font-bold text-emerald-600">{maxScore}</p>
          <p className="text-xs text-slate-500 mt-0.5">Meilleure performance</p>
        </div>
      </div>

      {/* Copies Table */}
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <h2 className="font-bold text-slate-900 text-lg">Copies individuelles des étudiants</h2>
          <span className="text-xs text-slate-400 font-medium">{attempts.length} copie(s) générée(s)</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-400">
              <tr>
                <th className="px-6 py-3">Étudiant</th>
                <th className="px-6 py-3">Statut</th>
                <th className="px-6 py-3">Horaires</th>
                <th className="px-6 py-3 text-right">Note Auto</th>
                <th className="px-6 py-3 text-right">Note Validée</th>
                <th className="px-6 py-3 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {attempts.map((a) => (
                <tr key={a.id} className="hover:bg-slate-50/70 transition">
                  <td className="px-6 py-4 font-semibold text-slate-800">
                    {a.student_name}
                    <p className="text-xs font-normal text-slate-400">{a.student_email}</p>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${
                        a.status === "GRADED"
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          : a.status === "SUBMITTED"
                          ? "bg-blue-50 text-blue-700 border border-blue-200"
                          : a.status === "IN_PROGRESS"
                          ? "bg-amber-50 text-amber-700 border border-amber-200 animate-pulse"
                          : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {a.status === "GRADED"
                        ? "Noté"
                        : a.status === "SUBMITTED"
                        ? "Soumis"
                        : a.status === "IN_PROGRESS"
                        ? "En train de composer"
                        : "Non démarré"}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-xs text-slate-500">
                    {a.submitted_at
                      ? `Remis le ${new Date(a.submitted_at).toLocaleTimeString("fr-FR")}`
                      : a.started_at
                      ? `Débuté à ${new Date(a.started_at).toLocaleTimeString("fr-FR")}`
                      : "—"}
                  </td>
                  <td className="px-6 py-4 text-right font-semibold text-slate-700">
                    {a.auto_score !== null ? `${a.auto_score.toFixed(2)} pts` : "—"}
                  </td>
                  <td className="px-6 py-4 text-right font-black text-indigo-700">
                    {a.final_score !== null ? `${a.final_score.toFixed(2)} pts` : "—"}
                  </td>
                  <td className="px-6 py-4 text-center">
                    <button
                      onClick={() => handleOpenReview(a)}
                      className="rounded-lg bg-indigo-50 px-3 py-1.5 text-xs font-bold text-indigo-700 hover:bg-indigo-100 transition"
                    >
                      Revoir / Noter →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal / Slide-over de Revue et Notation de la copie */}
      {selectedAttempt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="w-full max-w-4xl rounded-2xl bg-white shadow-2xl overflow-hidden my-8 max-h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="bg-slate-900 text-white p-6 flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-wider text-indigo-400 font-bold">
                  Copie d'examen individualisée
                </p>
                <h3 className="text-xl font-bold mt-1">{selectedAttempt.student_name}</h3>
                <p className="text-xs text-slate-400">{selectedAttempt.student_email}</p>
              </div>
              <button
                onClick={() => setSelectedAttempt(null)}
                className="rounded-lg bg-slate-800 px-3 py-1 text-sm font-semibold text-slate-300 hover:bg-slate-700"
              >
                ✕ Fermer
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-6 flex-1">
              {successMsg && (
                <div className="rounded-xl bg-emerald-50 p-4 border border-emerald-200 text-sm text-emerald-800">
                  {successMsg}
                </div>
              )}

              {/* Formulaire de validation / ajustement de la note par le professeur */}
              <form onSubmit={handleSaveGrade} className="rounded-2xl border border-indigo-200 bg-indigo-50/50 p-5 space-y-4">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div>
                    <h4 className="font-bold text-slate-900 text-base">Notation du Professeur</h4>
                    <p className="text-xs text-slate-500">
                      Note automatique proposée : <span className="font-bold text-slate-800">{selectedAttempt.auto_score ?? 0}</span> / {reviewData?.total_max_score ?? "N/A"}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 w-full sm:w-auto">
                    <div>
                      <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                        Note Finale
                      </label>
                      <input
                        type="number"
                        step={0.25}
                        min={0}
                        max={reviewData?.total_max_score ?? 100}
                        required
                        value={editScore}
                        onChange={(e) => setEditScore(parseFloat(e.target.value) || 0)}
                        className="w-28 rounded-lg border border-slate-300 bg-white p-2 text-base font-bold text-indigo-700 outline-none focus:border-indigo-600"
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={savingGrade}
                      className="mt-5 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-bold text-white shadow hover:bg-indigo-700 disabled:opacity-50"
                    >
                      {savingGrade ? "Enregistrement..." : "Valider la note"}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                    Commentaire pédagogique à destination de l'étudiant
                  </label>
                  <textarea
                    rows={2}
                    value={editComment}
                    onChange={(e) => setEditComment(e.target.value)}
                    placeholder="Ex: Bon raisonnement sur les requêtes SQL, attention à la normalisation 3NF."
                    className="w-full rounded-lg border border-slate-300 bg-white p-2.5 text-xs outline-none focus:border-indigo-600"
                  />
                </div>
              </form>

              {/* Questions et Réponses détaillées */}
              <div className="space-y-4">
                <h4 className="font-bold text-slate-900 text-sm uppercase tracking-wider text-slate-400">
                  Détail question par question
                </h4>

                {!reviewData ? (
                  <p className="text-sm text-slate-400 text-center py-6">Chargement des détails de la copie...</p>
                ) : (
                  reviewData.questions.map((rq: any, idx: number) => (
                    <div
                      key={rq.question_id}
                      className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex items-center gap-2">
                          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-100 text-xs font-black text-slate-700">
                            {idx + 1}
                          </span>
                          <span className="text-xs font-bold text-slate-500 capitalize">
                            [{rq.difficulty}]
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-xs font-extrabold text-indigo-700 bg-indigo-50 px-2.5 py-1 rounded-full">
                            Score : {rq.score_earned} / {rq.max_score} pts
                          </span>
                          <button
                            type="button"
                            onClick={() => handleCancelQuestion(rq.question_id)}
                            disabled={cancellingQId === rq.question_id}
                            className="text-xs font-semibold text-red-600 hover:text-red-800 border border-red-200 px-2 py-0.5 rounded bg-red-50 hover:bg-red-100 transition"
                          >
                            Annuler cette question (toute la classe)
                          </button>
                        </div>
                      </div>

                      <p className="text-sm font-semibold text-slate-900">{rq.statement}</p>

                      <div className="space-y-2 pt-2">
                        {rq.options.map((opt: any) => {
                          const isGood = opt.is_correct;
                          const wasChosen = opt.was_selected;
                          return (
                            <div
                              key={opt.id}
                              className={`p-3 rounded-lg text-xs flex items-center justify-between border ${
                                wasChosen && isGood
                                  ? "bg-emerald-50 border-emerald-300 text-emerald-950 font-semibold"
                                  : wasChosen && !isGood
                                  ? "bg-red-50 border-red-300 text-red-950 line-through"
                                  : isGood
                                  ? "bg-emerald-50/50 border-emerald-200 text-emerald-800"
                                  : "bg-slate-50 border-slate-200 text-slate-600"
                              }`}
                            >
                              <div className="flex items-center gap-2">
                                <span className="font-bold">
                                  {wasChosen ? "👉 [Coché par l'étudiant]" : "⚪"}
                                </span>
                                <span>{opt.text}</span>
                              </div>
                              <span className="font-bold">
                                {isGood ? "✓ Bonne réponse" : ""}
                              </span>
                            </div>
                          );
                        })}
                      </div>

                      {rq.explanation && (
                        <p className="text-xs text-slate-500 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                          <span className="font-bold text-slate-700">Explication :</span> {rq.explanation}
                        </p>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
