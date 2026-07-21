"""Pruebas de compatibilidad de URLs de PostgreSQL para Supabase."""

from app.core.config import normalize_database_url


def test_supabase_postgresql_url_uses_psycopg_and_ssl() -> None:
    database_url = (
        "postgresql://postgres:secret@db.lrhpnfcroynmaepxoglz.supabase.co:5432/postgres"
    )

    assert normalize_database_url(database_url) == (
        "postgresql+psycopg://postgres:secret@db.lrhpnfcroynmaepxoglz.supabase.co:5432/postgres"
        "?sslmode=require"
    )


def test_existing_ssl_option_is_preserved() -> None:
    database_url = "postgresql://postgres:secret@example.com/postgres?sslmode=verify-full"

    assert normalize_database_url(database_url).endswith("?sslmode=verify-full")


def test_sqlite_url_is_unchanged() -> None:
    assert normalize_database_url("sqlite:///./portoasiste.db") == "sqlite:///./portoasiste.db"


def test_incomplete_supabase_template_falls_back_to_sqlite() -> None:
    database_url = "postgresql://postgres:TU_PASSWORD_URL_ENCODED@db.TU_PROJECT_REF.supabase.co:5432/postgres"

    assert normalize_database_url(database_url) == "sqlite:///./portoasiste.db"
