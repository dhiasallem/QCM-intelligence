from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings


class Base(DeclarativeBase):
    pass


def get_engine():
    connect_args = {}
    if "postgres" in settings.database_url:
        connect_args = {"connect_timeout": 2}
    elif "sqlite" in settings.database_url:
        connect_args = {"check_same_thread": False}

    try:
        eng = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        with eng.connect() as conn:
            pass
        return eng
    except Exception as e:
        print(f"⚠️ PostgreSQL non accessible ({e}). Bascule automatique sur SQLite local (qcm.db).")
        sqlite_eng = create_engine("sqlite:///qcm.db", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=sqlite_eng)
        return sqlite_eng


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
