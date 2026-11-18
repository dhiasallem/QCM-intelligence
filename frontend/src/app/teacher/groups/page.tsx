"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function GroupsPage() {
  const [groups, setGroups] = useState<any[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [newGroupName, setNewGroupName] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const loadData = async () => {
    try {
      const gList = await api.groups.list();
      setGroups(gList);
      if (selectedGroup) {
        const refreshed = await api.groups.get(selectedGroup.id);
        setSelectedGroup(refreshed);
      }
    } catch (err: any) {
      setError(err.message || "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSelectGroup = async (g: any) => {
    try {
      const full = await api.groups.get(g.id);
      setSelectedGroup(full);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleCreateGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newGroupName.trim()) return;
    try {
      const created = await api.groups.create(newGroupName.trim());
      setNewGroupName("");
      setShowCreateModal(false);
      setSelectedGroup(created); // affiche directement le code d'accès du nouveau groupe
      setGroups(await api.groups.list());
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleCopyCode = async () => {
    if (!selectedGroup) return;
    try {
      await navigator.clipboard.writeText(selectedGroup.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Copie impossible : sélectionnez le code et copiez-le manuellement.");
    }
  };

  const handleDeleteGroup = async () => {
    if (!selectedGroup) return;
    if (!confirm(`Supprimer le groupe « ${selectedGroup.name} » ? Les étudiants n'en feront plus partie.`)) return;
    setError(null);
    try {
      await api.groups.delete(selectedGroup.id);
      setSelectedGroup(null);
      setGroups(await api.groups.list());
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleRegenerateCode = async () => {
    if (!selectedGroup) return;
    if (!confirm("Générer un nouveau code ? L'ancien code ne fonctionnera plus. Les étudiants déjà inscrits restent dans le groupe.")) return;
    try {
      const refreshed = await api.groups.regenerateCode(selectedGroup.id);
      setSelectedGroup(refreshed);
      setGroups(await api.groups.list());
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleRemoveStudent = async (studentId: number) => {
    if (!selectedGroup) return;
    try {
      await api.groups.removeStudent(selectedGroup.id, studentId);
      const refreshed = await api.groups.get(selectedGroup.id);
      setSelectedGroup(refreshed);
      await loadData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Groupes & Classes d'étudiants</h1>
          <p className="text-sm text-slate-500 mt-1">
            Créez un groupe puis communiquez son code d'accès à vos étudiants : ils le saisissent dans leur espace pour rejoindre la classe.
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-bold text-white shadow hover:bg-indigo-700 transition"
        >
          + Créer un groupe
        </button>
      </div>

      {error && (
        <div className="rounded-xl bg-red-50 p-4 border border-red-200 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Main 2-column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Groups List */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
          <h2 className="font-bold text-slate-800 text-base">Vos groupes ({groups.length})</h2>
          {groups.length === 0 ? (
            <p className="text-sm text-slate-400 py-6 text-center">Aucun groupe créé.</p>
          ) : (
            <div className="space-y-2">
              {groups.map((g) => (
                <button
                  key={g.id}
                  onClick={() => handleSelectGroup(g)}
                  className={`w-full text-left p-4 rounded-xl border transition flex items-center justify-between ${
                    selectedGroup?.id === g.id
                      ? "border-indigo-600 bg-indigo-50/70"
                      : "border-slate-100 bg-slate-50/50 hover:bg-slate-100"
                  }`}
                >
                  <div>
                    <p className="font-bold text-sm text-slate-900">{g.name}</p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {g.student_count} étudiant(s) • Code <span className="font-mono font-semibold text-slate-600">{g.code}</span>
                    </p>
                  </div>
                  <span className="text-xs text-indigo-600 font-semibold">Gérer →</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Selected Group Detail & Students Management */}
        <div className="lg:col-span-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          {selectedGroup ? (
            <div className="space-y-6">
              <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                <div>
                  <h2 className="text-xl font-bold text-slate-900">{selectedGroup.name}</h2>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {selectedGroup.students?.length || 0} étudiant(s) inscrits
                  </p>
                </div>
                <button
                  onClick={handleDeleteGroup}
                  className="rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-bold text-red-600 hover:bg-red-50 transition"
                >
                  Supprimer le groupe
                </button>
              </div>

              {/* Code d'accès du groupe */}
              <div className="rounded-xl bg-indigo-50 border border-indigo-200 p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-indigo-700">Code d'accès</p>
                  <p className="mt-1 font-mono text-3xl font-black tracking-[0.2em] text-indigo-900 select-all">
                    {selectedGroup.code}
                  </p>
                  <p className="text-xs text-indigo-700/80 mt-1">
                    Les étudiants saisissent ce code dans « Rejoindre un groupe » de leur espace.
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleCopyCode}
                    className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-bold text-white hover:bg-indigo-700 transition"
                  >
                    {copied ? "✓ Copié" : "Copier"}
                  </button>
                  <button
                    onClick={handleRegenerateCode}
                    className="rounded-lg border border-indigo-200 bg-white px-4 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-100 transition"
                  >
                    Changer le code
                  </button>
                </div>
              </div>

              {/* Students List */}
              <div className="divide-y divide-slate-100">
                {!selectedGroup.students || selectedGroup.students.length === 0 ? (
                  <p className="py-8 text-center text-sm text-slate-400">
                    Aucun étudiant pour l'instant. Partagez le code d'accès pour qu'ils rejoignent le groupe.
                  </p>
                ) : (
                  selectedGroup.students.map((s: any) => (
                    <div key={s.id} className="py-3 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-100 font-bold text-xs text-indigo-700">
                          {s.name.slice(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <p className="font-semibold text-sm text-slate-800">{s.name}</p>
                          <p className="text-xs text-slate-400">{s.email}</p>
                        </div>
                      </div>
                      <button
                        onClick={() => handleRemoveStudent(s.id)}
                        className="text-xs font-semibold text-red-600 hover:text-red-800"
                      >
                        Retirer
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          ) : (
            <div className="py-16 text-center text-slate-400">
              Sélectionnez un groupe dans la colonne de gauche pour afficher et gérer ses étudiants.
            </div>
          )}
        </div>
      </div>

      {/* Modal Création Groupe */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl space-y-4">
            <h3 className="text-lg font-bold text-slate-900">Créer un nouveau groupe</h3>
            <form onSubmit={handleCreateGroup} className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">
                  Nom du groupe / Promotion
                </label>
                <input
                  type="text"
                  required
                  value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)}
                  placeholder="Ex: Licence 1 Informatique - Groupe A"
                  className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-indigo-600"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-bold text-white hover:bg-indigo-700"
                >
                  Créer
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
