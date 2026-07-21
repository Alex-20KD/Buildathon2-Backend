"""Motor y sesión SQLAlchemy para SQLite, sin migraciones."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base declarativa de las tablas del MVP."""


def get_db() -> Generator[Session, None, None]:
    """Abre una sesión breve por solicitud HTTP."""
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()


def init_db() -> None:
    """Crea las tablas al boot, suficiente para el alcance de hackathon."""
    from app.db import models  # noqa: F401 - Registra ChatHistory antes de create_all.

    Base.metadata.create_all(bind=engine)
