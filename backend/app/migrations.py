"""Mises à jour légères du schéma, appliquées au démarrage.

`Base.metadata.create_all` crée les tables manquantes mais n'ajoute jamais de colonne
à une table existante : on le fait ici pour les bases créées avec une version antérieure.
"""
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models.user import Group, generate_group_code


def ensure_group_codes(engine: Engine) -> None:
    columns = {c["name"] for c in inspect(engine).get_columns("student_groups")}
    if "code" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE student_groups ADD COLUMN code VARCHAR(12)"))

    # Attribuer un code aux groupes qui n'en ont pas encore
    with Session(engine) as db:
        used = set(db.scalars(select(Group.code).where(Group.code.is_not(None))))
        for group in db.scalars(select(Group).where(Group.code.is_(None))):
            code = generate_group_code()
            while code in used:
                code = generate_group_code()
            used.add(code)
            group.code = code
        db.commit()

    with engine.begin() as conn:
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_student_groups_code ON student_groups (code)"
        ))


def run_migrations(engine: Engine) -> None:
    ensure_group_codes(engine)
