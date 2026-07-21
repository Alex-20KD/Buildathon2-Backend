"""Pruebas de disponibilidad y CORS de la API."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app import main
from app.main import app


def test_health_check_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_starts_when_history_database_is_unavailable(monkeypatch) -> None:
    def unavailable_database() -> None:
        raise SQLAlchemyError("Base de datos no disponible")

    monkeypatch.setattr(main, "init_db", unavailable_database)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert app.state.history_enabled is False


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "https://buildathon2-frontend.vercel.app",
    ],
)
def test_cors_allows_configured_frontend(origin: str) -> None:
    with TestClient(app) as client:
        response = client.options(
            "/api/chat",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
