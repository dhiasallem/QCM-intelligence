"use client";

import React, { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

// Valeur pour <input type="datetime-local"> : "AAAA-MM-JJTHH:MM" en heure LOCALE.
// (toISOString() donne l'heure UTC, ce qui décalait les dates proposées d'une heure ou plus.)
function toLocalInputValue(d: Date): string {
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

export default function SessionsPage() {
  const searchParams = useSearchParams();
  const preselectedQuizId = searchParams.get("new_for_quiz");

  const [sessions, setSessions] = useState<any[]>([]);
  const [quizzes, setQuizzes] = useState<any[]>([]);
  const [groups, setGroups] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(!!preselectedQuizId);
  const [publishingId, setPublishingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Formulaire nouvelle session
  const [quizId, setQuizId] = useState<number | "">(preselectedQuizId ? Number(preselectedQuizId) : "");
  const [groupId, setGroupId] = useState<number | "">("");
  const [opensAt, setOpensAt] = useState("");
  const [closesAt, setClosesAt] = useState("");
  const [durationMinutes, setDurationMinutes] = useState(30);
  const [questionsPerStudent, setQuestionsPerStudent] = useState(5);
  const [pointsPerQuestion, setPointsPerQuestion] = useState(1.0);
  const [scoringRule, setScoringRule] = useState("ALL_OR_NOTHING");
  const [penalty, setPenalty] = useState(0.0);

  const loadData = async () => {
    try {
      const [sList, qList, gList] = await Promise.all([
        api.sessions.list(),
        api.quizzes.list(),
        api.groups.list(),
      ]);
      setSessions(sList);
      setQuizzes(qList.filter((q) => q.status === "VALIDATED"));
      setGroups(gList);

      // Pré-remplir les dates par défaut (ouverture maintenant, clôture dans 2h)
      const now = new Date();
      const inTwoHours = new Date(now.getTime() + 2 * 60 * 60 * 1000);
      setOpensAt(toLocalInputValue(now));
      setClosesAt(toLocalInputValue(inTwoHours));
    } catch (err: any) {
      setError(err.message || "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quizId || !groupId) return;
    setError(null);

    try {
      await api.sessions.create({
        quiz_id: Number(quizId),
        group_id: Number(groupId),
        opens_at: new Date(opensAt).toISOString(),
        closes_at: new Date(closesAt).toISOString(),
        duration_minutes: Number(durationMinutes),
        questions_per_student: Number(questionsPerStudent),
        points_per_question: Number(pointsPerQuestion),
        scoring_rule: scoringRule,
        penalty: Number(penalty),
      });

      setShowCreateModal(false);
      await loadData();
    } catch (err: any) {
      setError(err.message || "Erreur lors de la création de la session");
    }
  };

  const handlePublish = async (sessId: number) => {
    if (!confirm("Voulez-vous publier cette session ? Les copies individualisées vont être générées pour chaque étudiant du groupe.")) return;
    setPublishingId(sessId);
    setError(null);
    try {
      await api.sessions.publish(sessId);
      await loadData();
    } catch (err: any) {
      setError(err.message || "Erreur lors de la publication");
    } finally {
      setPublishingId(null);
    }
  };

  const handleDelete = async (s: any) => {
    const hasCopies = s.total_attempts > 0;
    const message = hasCopies
      ? `Supprimer la session "${s.quiz_subject}" (${s.group_name}) ?\n\n` +
        `⚠️ Les ${s.total_attempts} copie(s) seront supprimées, dont ${s.submitted_attempts} déjà rendue(s), avec leurs réponses et leurs notes. Cette action est irréversible.`
      : `Supprimer la session "${s.quiz_subject}" (${s.group_name}) ?`;
    if (!confirm(message)) return;
    setError(null);
    try {
      await api.sessions.delete(s.id, hasCopies);
      setSessions((prev) => prev.filter((x) => x.id !== s.id));
    } catch (err: any) {
      setError(err.message || "Erreur lors de la suppression");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Sessions d'examen</h1>
          <p className="text-sm text-slate-500 mt-1">
            Planifiez, distribuez des copies individualisées et suivez la passation en direct.
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-bold text-white shadow hover:bg-indigo-700 transition"
        >
          + Programmer un examen
        </button>
      </div>

      {error && (
        <div className="rounded-xl bg-red-50 p-4 border border-red-200 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-slate-500">Chargement des sessions...</div>
      ) : sessions.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center">
          <p className="text-base font-semibold text-slate-700">Aucune session d'examen planifiée.</p>
          <p className="mt-1 text-sm text-slate-400">
            Associez un QCM validé à un groupe d'étudiants pour lancer une session.
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="mt-5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-indigo-700 transition"
          >
            Créer ma première session
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sessions.map((s) => (
            <div
              key={s.id}
              className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm hover:shadow-md transition flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-3">
                  <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
                    Groupe : {s.group_name}
                  </span>
                  <span
                    className={`text-xs font-bold px-2.5 py-1 rounded-full ${
                      s.status === "OPEN"
                        ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                        : s.status === "DRAFT"
                        ? "bg-amber-50 text-amber-700 border border-amber-200"
                        : "bg-slate-100 text-slate-700"
                    }`}
                  >
                    {s.status === "OPEN" ? "En cours" : s.status === "DRAFT" ? "Brouillon (Non publié)" : "Clôturé"}
                  </span>
                </div>

                <h2 className="text-lg font-bold text-slate-900">{s.quiz_subject}</h2>

                <div className="mt-4 space-y-1.5 text-xs text-slate-600 bg-slate-50 rounded-xl p-3">
                  <p>
                    ⏱️ <span className="font-semibold text-slate-700">Durée :</span> {s.duration_minutes} minutes
                  </p>
                  <p>
                    🎲 <span className="font-semibold text-slate-700">Questions tirées :</span> {s.questions_per_student}
                  </p>
                  <p>
                    📊 <span className="font-semibold text-slate-700">Copies remises :</span> {s.submitted_attempts} / {s.total_attempts}
                  </p>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between gap-3">
                <button
                  onClick={() => handleDelete(s)}
                  className="shrink-0 text-xs font-semibold text-red-600 hover:text-red-800 transition"
                >
                  Supprimer
                </button>
                {s.status === "DRAFT" ? (
                  <button
                    onClick={() => handlePublish(s.id)}
                    disabled={publishingId === s.id}
                    className="w-full rounded-lg bg-emerald-600 py-2 text-xs font-bold text-white shadow hover:bg-emerald-700 transition"
                  >
                    {publishingId === s.id ? "Génération des copies..." : "Publier & Distribuer aux étudiants"}
                  </button>
                ) : (
                  <a
                    href={`/teacher/sessions/${s.id}`}
                    className="w-full text-center rounded-lg bg-indigo-50 py-2 text-xs font-bold text-indigo-700 hover:bg-indigo-100 transition"
                  >
                    Tableau de bord & Correction ({s.submitted_attempts} copies) →
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal Créer Session */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl space-y-5 my-8">
            <h3 className="text-xl font-bold text-slate-900">Programmer une session d'examen</h3>
            
            <form onSubmit={handleCreateSession} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Sélectionnez le QCM validé
                </label>
                <select
                  required
                  value={quizId}
                  onChange={(e) => setQuizId(Number(e.target.value))}
                  className="w-full rounded-lg border border-slate-300 bg-white p-2.5 text-sm outline-none focus:border-indigo-600"
                >
                  <option value="">Choisir un QCM validé...</option>
                  {quizzes.map((q) => (
                    <option key={q.id} value={q.id}>
                      {q.subject} ({q.specialty} - {q.level})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Groupe d'étudiants concerné
                </label>
                <select
                  required
                  value={groupId}
                  onChange={(e) => setGroupId(Number(e.target.value))}
                  className="w-full rounded-lg border border-slate-300 bg-white p-2.5 text-sm outline-none focus:border-indigo-600"
                >
                  <option value="">Choisir un groupe...</option>
                  {groups.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.name} ({g.student_count} étudiants)
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Ouverture
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={opensAt}
                    onChange={(e) => setOpensAt(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs outline-none focus:border-indigo-600"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Clôture
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={closesAt}
                    onChange={(e) => setClosesAt(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 p-2 text-xs outline-none focus:border-indigo-600"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Durée (min)
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={240}
                    required
                    value={durationMinutes}
                    onChange={(e) => setDurationMinutes(Number(e.target.value))}
                    className="w-full rounded-lg border border-slate-300 p-2 text-sm outline-none focus:border-indigo-600"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Questions tirées (N)
                  </label>
                  <input
                    type="number"
                    min={1}
                    required
                    value={questionsPerStudent}
                    onChange={(e) => setQuestionsPerStudent(Number(e.target.value))}
                    className="w-full rounded-lg border border-slate-300 p-2 text-sm outline-none focus:border-indigo-600"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Points / quest.
                  </label>
                  <input
                    type="number"
                    step={0.25}
                    min={0.25}
                    required
                    value={pointsPerQuestion}
                    onChange={(e) => setPointsPerQuestion(Number(e.target.value))}
                    className="w-full rounded-lg border border-slate-300 p-2 text-sm outline-none focus:border-indigo-600"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Règle de notation pour choix multiples
                </label>
                <select
                  value={scoringRule}
                  onChange={(e) => setScoringRule(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-white p-2 text-sm outline-none focus:border-indigo-600"
                >
                  <option value="ALL_OR_NOTHING">Tout ou rien (point accordé si 100% exact)</option>
                  <option value="PARTIAL">Points partiels proportionnels</option>
                  <option value="PARTIAL_PENALTY">Points partiels avec pénalité sur mauvaise réponse</option>
                </select>
              </div>

              {scoringRule === "PARTIAL_PENALTY" && (
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Pénalité par mauvaise réponse (ex: 0.5)
                  </label>
                  <input
                    type="number"
                    step={0.1}
                    min={0}
                    value={penalty}
                    onChange={(e) => setPenalty(Number(e.target.value))}
                    className="w-full rounded-lg border border-slate-300 p-2 text-sm outline-none focus:border-indigo-600"
                  />
                </div>
              )}

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-bold text-white shadow hover:bg-indigo-700"
                >
                  Enregistrer la session
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
