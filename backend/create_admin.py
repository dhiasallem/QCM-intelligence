from getpass import getpass

from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.security import hash_password

name = input("Nom : ").strip()
email = input("Email : ").strip().lower()
password = getpass("Mot de passe (8 caractères minimum) : ")

if len(password) < 8:
    raise SystemExit("Mot de passe trop court")

with SessionLocal() as db:
    if db.scalar(select(User).where(User.email == email)):
        raise SystemExit("Cet email existe déjà")
    db.add(User(name=name, email=email, password_hash=hash_password(password), role="admin"))
    db.commit()
    print("Administrateur créé.")