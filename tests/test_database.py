"""Pruebas de la persistencia SQLite del MVP."""

from sqlalchemy import inspect

from app.db.database import engine, init_db


def test_sqlite_chat_history_table_is_created() -> None:
    """La tabla de historial se crea automáticamente, sin migraciones."""
    init_db()

    inspector = inspect(engine)
    assert "chat_history" in inspector.get_table_names()
