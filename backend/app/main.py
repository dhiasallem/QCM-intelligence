from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db, Base, engine, SessionLocal
from app.migrations import run_migrations
from app.models.user import User
from app.routers import auth, users, quizzes, groups, sessions, attempts
from app.services.quiz_service import recover_interrupted_generations


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Créer les tables si nécessaire
    Base.metadata.create_all(bind=engine)
    run_migrations(engine)
    # Peupler les données de démo si la base est vide
    with SessionLocal() as db:
        if not db.query(User).first():
            from app.services.seed_service import seed
            seed()
        recovered = recover_interrupted_generations(db)
        if recovered:
            print(f"⚠️ {recovered} génération(s) IA interrompue(s) passée(s) en échec (à relancer).")
    yield


app = FastAPI(
    title="QCM API - Agent IA & Examens Individualisés",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(groups.router)
app.include_router(quizzes.router)
app.include_router(quizzes.questions_router)
app.include_router(sessions.router)
app.include_router(attempts.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"database": "ok"}
