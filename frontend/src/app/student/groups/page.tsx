"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function StudentGroupsPage() {
  const [groups, setGroups] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [code, setCode] = useState("");
  const [joining, setJoining] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadGroups = async () => {
    try {
      setGroups(await api.groups.mine());
    } catch (err: any) {
      setError(err.message || "Erreur de chargement des groupes");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGroups();
  }, []);

  const handleJoin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code.trim()) return;
    setJoining(true);
    setError(null);
    setSuccess(null);
    try {
      const res = await api.groups.join(code.trim());
      setCode("");
      setSuccess(
        `Vous avez rejoint « ${res.group.name} » (${res.group.teacher_name}).` +
          (res.new_exams > 0 ? ` ${res.new_exams} examen(s) vous ont été attribués.` : "")
      );
      await loadGroups();
    } catch (err: any) {
      setError(err.message || "Impossible de rejoindre ce groupe");
    } finally {
      setJoining(false);
    }
  };

  const handleLeave = async (g: any) => {
    if (!confirm(`Quitter le groupe « ${g.name} » ? Les examens de ce groupe que vous n'avez pas commencés ne vous seront plus proposés. Vos copies déjà rendues et vos notes sont conservées.`)) return;
    setError(null);
    setSuccess(null);
    try {
      await api.groups.leave(g.id);
      setSuccess(`Vous avez quitté « ${g.name} ».`);
      await loadGroups();
    } catch (err: any) {
      setError(err.message || "Impossible de quitter ce groupe");
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Rejoindre un groupe</h1>
        <p className="text-sm text-slate-500 mt-1">
          Saisissez le code d'accès donné par votre enseignant pour rejoindre sa classe et recevoir ses QCM.
        </p>
      </div>

      <form
        onSubmit={handleJoin}
        className="max-w-xl rounded-2xl border border-indigo-200 bg-indigo-50/60 p-6 space-y-4"
      >
        <label htmlFor="group-code" className="block text-sm font-semibold text-slate-800">
          Code d'accès du groupe
        </label>
        <div className="flex gap-2">
          <input
            id="group-code"
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder="Ex : K7XQ2PM"
            maxLength={12}
            autoComplete="off"
            className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 font-mono text-base tracking-widest uppercase outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100"
          />
          <button
            type="submit"
            disabled={joining || code.trim().length < 4}
            className="shrink-0 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-bold text-white hover:bg-indigo-700 disabled:opacity-50 transition"
          >
            {joining ? "Connexion..." : "Rejoindre"}
          </button>
        </div>
        {error && <p className="text-sm font-medium text-red-600">{error}</p>}
        {success && (
          <p className="text-sm font-medium text-emerald-700">
            {success}{" "}
            <a href="/student" className="underline underline-offset-2 hover:text-emerald-900">
              Voir mes examens →
            </a>
          </p>
        )}
      </form>

      <div className="space-y-4">
        <h2 className="text-lg font-bold text-slate-900">Mes groupes ({groups.length})</h2>
        {loading ? (
          <p className="text-sm text-slate-500">Chargement...</p>
        ) : groups.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-400">
            Vous n'êtes inscrit dans aucun groupe pour l'instant.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {groups.map((g) => (
              <div
                key={g.id}
                className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm flex flex-col justify-between gap-4"
              >
                <div>
                  <p className="text-base font-bold text-slate-900">{g.name}</p>
                  <p className="text-sm text-slate-500 mt-1">Enseignant : {g.teacher_name}</p>
                  <p className="text-xs text-slate-400 mt-0.5">{g.student_count} membre(s)</p>
                </div>
                <button
                  onClick={() => handleLeave(g)}
                  className="self-start text-xs font-semibold text-red-600 hover:text-red-800 transition"
                >
                  Quitter le groupe
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
