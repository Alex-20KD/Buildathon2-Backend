"""Prueba del PDF local sin usar OpenAI."""

from fastapi.testclient import TestClient

from app.main import app


def test_generate_pdf_for_supported_tramite() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/tramites/generar",
            params={
                "tramite": "Permiso de Funcionamiento",
                "nombre_solicitante": "Ana Pérez",
            },
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
