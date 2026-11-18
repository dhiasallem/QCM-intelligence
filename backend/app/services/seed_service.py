from datetime import datetime, timezone, timedelta
from app.db import SessionLocal, Base, engine
from app.models.user import User, Group
from app.models.quiz import Quiz, Question, Option
from app.models.exam import ExamSession, Attempt, AttemptQuestion
from app.security import hash_password
from app.services.sampling_service import stratified_sample


def seed():
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        existing_prof = db.query(User).filter(User.email == "prof@univ.fr").first()
        if existing_prof:
            return

        print("🌱 Initialisation automatique des comptes de démo...")
        prof = User(
            name="Professeur Martin",
            email="prof@univ.fr",
            password_hash=hash_password("password123"),
            role="teacher",
        )
        student1 = User(
            name="Ada Lovelace",
            email="ada@univ.fr",
            password_hash=hash_password("password123"),
            role="student",
        )
        student2 = User(
            name="Alan Turing",
            email="alan@univ.fr",
            password_hash=hash_password("password123"),
            role="student",
        )
        student3 = User(
            name="Grace Hopper",
            email="grace@univ.fr",
            password_hash=hash_password("password123"),
            role="student",
        )

        db.add_all([prof, student1, student2, student3])
        db.commit()
        db.refresh(prof)
        db.refresh(student1)
        db.refresh(student2)
        db.refresh(student3)

        group = Group(name="Licence 1 Informatique - Groupe A", teacher_id=prof.id)
        group.students = [student1, student2, student3]
        db.add(group)
        db.commit()
        db.refresh(group)

        quiz = Quiz(
            teacher_id=prof.id,
            specialty="Informatique",
            subject="Bases de données relationnelles & SQL",
            level="Licence 1",
            nb_questions=5,
            chapters="Modèle relationnel, Algèbre relationnelle, Requêtes SELECT, Clés et intégrité",
            provider="gemini",
            status="VALIDATED",
        )
        db.add(quiz)
        db.flush()

        questions_data = [
            ("Quelle clause SQL est utilisée pour filtrer les lignes retournées par une requête ?", "facile", "Requêtes SELECT", "WHERE filtre les lignes alors que HAVING filtre les groupes.", [
                ("WHERE", True), ("HAVING", False), ("ORDER BY", False), ("GROUP BY", False)
            ]),
            ("Qu'est-ce qu'une clé primaire dans une table relationnelle ?", "facile", "Modèle relationnel", "Une clé primaire identifie de façon unique et non nulle chaque tuple d'une relation.", [
                ("Un identifiant unique et non nul pour chaque enregistrement", True),
                ("Une clé qui fait référence à une autre table", False),
                ("Un index optionnel pour accélérer la recherche", False),
                ("Une colonne contenant uniquement des entiers pairs", False)
            ]),
            ("Quelle est la différence fondamentale entre WHERE et HAVING en SQL ?", "moyen", "Requêtes SELECT", "WHERE filtre les lignes individuelles avant agrégation, HAVING filtre après agrégation.", [
                ("WHERE filtre avant GROUP BY, HAVING filtre les résultats agrégés", True),
                ("WHERE s'utilise uniquement avec des chaînes de caractères", False),
                ("HAVING ne fonctionne qu'avec des jointures externes", False),
                ("Il n'y a aucune différence, ce sont des synonymes", False)
            ]),
            ("Quel type de jointure conserve toutes les lignes de la table de gauche, même sans correspondance ?", "moyen", "Jointures SQL", "LEFT JOIN préserve les lignes de gauche avec des NULLs à droite en l'absence de correspondance.", [
                ("LEFT OUTER JOIN", True),
                ("INNER JOIN", False),
                ("RIGHT JOIN", False),
                ("CROSS JOIN", False)
            ]),
            ("Qu'assure la contrainte d'intégrité référentielle ?", "moyen", "Clés et intégrité", "Elle garantit que la valeur d'une clé étrangère existe bien dans la clé primaire de la table référencée.", [
                ("Qu'une clé étrangère pointe toujours vers un enregistrement existant", True),
                ("Que la base de données est sauvegardée quotidiennement", False),
                ("Que les mots de passe sont hachés", False),
                ("Que chaque table possède au moins deux colonnes", False)
            ]),
            ("En algèbre relationnelle, quelle opération correspond à la sélection de colonnes ?", "difficile", "Algèbre relationnelle", "La projection (symbole pi) sélectionne des colonnes, la restriction (sigma) sélectionne des lignes.", [
                ("La projection (π)", True),
                ("La restriction (σ)", False),
                ("L'union (∪)", False),
                ("Le produit cartésien (×)", False)
            ]),
            ("Quelle propriété ACID garantit qu'une transaction est exécutée entièrement ou pas du tout ?", "difficile", "Transactions", "L'Atomicité garantit le tout ou rien d'une transaction.", [
                ("Atomicité", True),
                ("Cohérence", False),
                ("Isolation", False),
                ("Durabilité", False)
            ]),
            ("Quel index est particulièrement adapté pour des colonnes à faible cardinalité (ex: statut booléen) ?", "difficile", "Indexation", "Les index bitmap sont très efficaces pour les colonnes ayant peu de valeurs distinctes.", [
                ("Index Bitmap", True),
                ("Index B-Tree", False),
                ("Index Hash", False),
                ("Index Clustered", False)
            ]),
            ("Quelle commande SQL permet de supprimer la structure complète d'une table et ses données ?", "facile", "DDL", "DROP TABLE supprime la table du schéma, DELETE supprime les lignes.", [
                ("DROP TABLE", True),
                ("DELETE FROM", False),
                ("TRUNCATE", False),
                ("REMOVE TABLE", False)
            ]),
            ("Quelle forme normale élimine les dépendances transitives non-clé ?", "difficile", "Normalisation", "La 3ème Forme Normale (3NF) requiert la 2NF et l'absence de dépendance transitive.", [
                ("3ème Forme Normale (3NF)", True),
                ("1ère Forme Normale (1NF)", False),
                ("2ème Forme Normale (2NF)", False),
                ("Forme de Boyce-Codd (BCNF)", False)
            ]),
        ]

        for stmt, diff, chap, exp, opts in questions_data:
            q = Question(
                quiz_id=quiz.id,
                statement=stmt,
                difficulty=diff,
                chapter=chap,
                explanation=exp,
                status="VALIDATED",
            )
            q.options = [Option(text=t, is_correct=c) for t, c in opts]
            db.add(q)
        db.commit()

        now = datetime.now(timezone.utc)
        sess = ExamSession(
            quiz_id=quiz.id,
            group_id=group.id,
            opens_at=now - timedelta(minutes=10),
            closes_at=now + timedelta(hours=3),
            duration_minutes=20,
            questions_per_student=5,
            points_per_question=2.0,
            scoring_rule="ALL_OR_NOTHING",
            status="OPEN",
        )
        db.add(sess)
        db.commit()
        db.refresh(sess)

        all_questions = quiz.questions
        for s in group.students:
            seed_str = f"{sess.id}_{s.id}"
            sampled = stratified_sample(all_questions, sess.questions_per_student, seed_str)
            attempt = Attempt(
                session_id=sess.id,
                student_id=s.id,
                seed=seed_str,
                status="NOT_STARTED",
            )
            db.add(attempt)
            db.flush()
            for it in sampled:
                db.add(
                    AttemptQuestion(
                        attempt_id=attempt.id,
                        question_id=it["question_id"],
                        position=it["position"],
                        option_order=it["option_order"],
                    )
                )

        db.commit()
        print("✅ Comptes de démo prêts : prof@univ.fr / ada@univ.fr (mdp: password123)")
