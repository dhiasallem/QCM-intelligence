"""Crée un compte étudiant.

Usage :
    python create_student.py "Nom Prénom" email@univ.fr motdepasse [--group "Nom du groupe"]
"""
import argparse

from sqlalchemy import select

from app.db import SessionLocal
from app.models.user import Group, User
from app.security import hash_password

parser = argparse.ArgumentParser(description="Créer un étudiant")
parser.add_argument("name")
parser.add_argument("email")
parser.add_argument("password")
parser.add_argument("--group", help="Nom d'un groupe existant auquel ajouter l'étudiant")
args = parser.parse_args()

email = args.email.strip().lower()
if len(args.password) < 8:
    raise SystemExit("Mot de passe trop court (8 caractères minimum)")

with SessionLocal() as db:
    if db.scalar(select(User).where(User.email == email)):
        raise SystemExit("Cet email existe déjà")

    student = User(
        name=args.name.strip(),
        email=email,
        password_hash=hash_password(args.password),
        role="student",
    )
    db.add(student)

    if args.group:
        group = db.scalar(select(Group).where(Group.name == args.group))
        if not group:
            raise SystemExit(f"Groupe introuvable : {args.group}")
        group.students.append(student)

    db.commit()
    print(f"Étudiant créé : {student.name} <{student.email}>" + (f" (groupe : {args.group})" if args.group else ""))
