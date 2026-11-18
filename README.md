# QCM Intelligence - Plateforme d'évaluation individualisée par IA

Application web de génération, passation et correction de QCM assistée par IA (Gemini, avec Mistral en secours optionnel). Les enseignants créent des classes que les étudiants rejoignent avec un code d'accès. Chaque étudiant reçoit une copie individualisée et déterministe, avec un minuteur contrôlé par le serveur et une correction automatique validée par l'enseignant.

---

## 🚀 Fonctionnalités clés

1. **Comptes et classes** :
   - Inscription libre en tant qu'**enseignant** ou **étudiant** (page `/register`) ;.
   - L'enseignant crée des **groupes** ; chaque groupe reçoit un **code d'accès** de 7 caractères, copiable et régénérable.
   - L'étudiant saisit le code dans son espace pour rejoindre le groupe. Il reçoit les examens publiés pour ce groupe, y compris ceux déjà ouverts au moment où il le rejoint.
2. **Génération par IA robuste** :
   - Banque élargie de $2N$ questions (30 % faciles, 50 % moyennes, 20 % difficiles), générée **par lots de 10** pour résister à la forte charge des fournisseurs.
   - Nouveaux essais avec attente croissante en cas de surcharge (503/429), puis bascule vers le fournisseur suivant (`AI_PROVIDER_ORDER`).
   - Validation Pydantic question par question : une question mal formée est écartée sans faire échouer le lot. Les doublons entre lots sont supprimés.
   - Une génération interrompue par un redémarrage du serveur passe en échec et peut être relancée.
3. **Revue et validation par l'enseignant** :
   - L'enseignant relit, modifie, supprime ou valide la banque ; un examen ne peut être programmé qu'avec une banque validée.
   - Une banque peut être supprimée tant qu'aucune session ne l'utilise.
4. **Copies individualisées par tirage stratifié déterministe** :
   - Échantillonnage stratifié par difficulté et par chapitre.
   - Tirage et mélange (ordre des questions et des options) déterministes, basés sur `seed = f"{session_id}_{student_id}"`.
5. **Passation en ligne sécurisée** :
   - Minuteur contrôlé par le serveur (`deadline_at`) et sauvegarde automatique toutes les 20 secondes.
   - **Zéro fuite** : ni bonne réponse (`is_correct`) ni explication n'est envoyée au navigateur pendant l'épreuve.
   - Soumission manuelle, ou automatique à l'expiration du temps. À la clôture de la session, les copies encore en cours sont soumises et notées.
6. **Correction et notation** :
   - 3 règles de calcul : *Tout ou rien*, *Partiel proportionnel*, *Partiel avec pénalité*.
   - Tableau de bord enseignant : ajustement des notes, commentaires, statistiques de classe, export CSV.
   - Annulation d'une question défectueuse avec recalcul immédiat pour toute la classe.
   - Suppression d'une session (avec confirmation renforcée si des copies ont déjà été rendues, et trace dans le journal d'audit).

---

## 🛠️ Architecture et stack technique

- **Backend** : FastAPI (Python 3.13), SQLAlchemy 2.0, Pydantic v2, Argon2 / JWT.
- **Frontend** : Next.js 15 (App Router), React 19, Tailwind CSS, TypeScript.
- **Base de données** : PostgreSQL 16 (port **5433**). Si PostgreSQL est inaccessible, le backend bascule automatiquement sur un fichier SQLite local `backend/qcm.db`.
- **Modèles IA** : Google Gemini (`gemini-3.5-flash`, avec repli automatique sur `gemini-3.5-flash-lite`) et, en option, Mistral (`mistral-small-latest`).

Le schéma de la base est créé au démarrage du backend (`create_all`), et les ajouts de colonnes sur une base existante sont appliqués par `app/migrations.py`. Il n'est donc pas nécessaire de lancer Alembic.

---

## ⚙️ Démarrage rapide

### 1. Base de données

```bash
docker compose up -d
```

### 2. Configuration (`.env` à la racine du projet)

Copiez `.env.example` en `.env`, puis renseignez au minimum `GEMINI_API_KEY` et `JWT_SECRET` :
```env
DATABASE_URL=postgresql+psycopg://qcm:qcm_pass@127.0.0.1:5433/qcm
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=une_longue_cle_secrete
GEMINI_API_KEY=votre_cle_gemini
GEMINI_MODEL=gemini-3.5-flash
MISTRAL_API_KEY=            # optionnel : relais si Gemini est indisponible
AI_PROVIDER_ORDER=gemini,mistral
```

### 3. Lancement

Le plus simple, sous Windows, depuis la racine du projet :
```powershell
.\run_dev.ps1
```
Ce script ouvre deux fenêtres : le backend sur http://localhost:8000 (documentation Swagger sur `/docs`) et le frontend sur http://localhost:3000. Gardez-les ouvertes.

Ou manuellement :
```bash
# Backend
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --port 8000

# Frontend (autre terminal)
cd frontend
npm install
npm run dev
```

### 4. Comptes de démonstration

Ils sont créés **automatiquement au premier démarrage** si la base est vide (sinon, `python seed_demo.py` dans `backend`) :
- **Enseignant** : `prof@univ.fr` / `password123`
- **Étudiants** : `ada@univ.fr`, `alan@univ.fr`, `grace@univ.fr` / `password123`

Vous pouvez aussi créer vos propres comptes depuis la page **Créer un compte**.

### 5. Scripts d'administration (dossier `backend`)

```bash
python create_admin.py                     # crée un administrateur (saisie interactive)
python create_student.py "Nom" email@univ.fr motdepasse [--group "Nom du groupe"]
```

### 6. Tests automatisés

```bash
cd backend
pytest -q
```
Les tests couvrent le tirage stratifié, les règles de notation, l'absence de fuite des réponses, le cycle de vie complet d'un examen, l'inscription et les codes de groupe, la génération IA par lots (avec fournisseurs simulés) et les suppressions.

---

## ❓ Dépannage

| Symptôme | Cause probable |
|---|---|
| `ERR_CONNECTION_REFUSED` sur `:8000` dans le navigateur | Le backend n'est pas lancé : relancez `run_dev.ps1`. |
| « Le service d'IA est saturé… » | Gemini est surchargé (erreur 503). C'est temporaire : relancez la génération. Pour éviter l'attente, vous pouvez aussi mettre `GEMINI_MODEL=gemini-3.5-flash-lite`. |
| Banque bloquée en « Génération en cours » | Redémarrez le backend : elle passera en échec et pourra être relancée. |
