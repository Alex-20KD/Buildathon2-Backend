"""Pruebas del contrato de chat sin llamar a servicios externos."""

from fastapi.testclient import TestClient
from sqlalchemy import select

from app import main
from app.db.database import SessionLocal
from app.db.models import ChatHistory
from app.rag.knowledge_base import load_tramites
from app.rag.vector_store import MissingOpenAIKeyError, RetrievedTramite


def _retrieved_tramite() -> RetrievedTramite:
    tramite = load_tramites()[0]
    return RetrievedTramite(
        nombre=tramite.nombre,
        descripcion=tramite.descripcion,
        requisitos=tramite.requisitos,
        costo_estimado=tramite.costo_estimado,
        tiempo_estimado=tramite.tiempo_estimado,
        palabras_clave=tramite.palabras_clave,
    )


def test_chat_returns_structured_response_and_persists_history(monkeypatch) -> None:
    class FakeRetriever:
        def retrieve(self, query: str) -> list[RetrievedTramite]:
            assert query == "Quiero abrir un restaurante"
            return [_retrieved_tramite()]

    class FakeChain:
        def answer(self, **_: object) -> str:
            return "Trámite identificado: Permiso de Funcionamiento"

    monkeypatch.setattr(main, "get_retriever", lambda: FakeRetriever())
    monkeypatch.setattr(main, "get_chat_chain", lambda: FakeChain())

    with TestClient(main.app) as client:
        response = client.post(
            "/api/chat",
            json={"message": "Quiero abrir un restaurante", "session_id": "sesion-prueba"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tramite_detectado"] == "Permiso de Funcionamiento"
    assert payload["session_id"] == "sesion-prueba"

    with SessionLocal() as database:
        history = database.scalar(
            select(ChatHistory).where(ChatHistory.session_id == "sesion-prueba")
        )
    assert history is not None
    assert history.user_message == "Quiero abrir un restaurante"


def test_chat_reports_missing_openai_configuration(monkeypatch) -> None:
    def missing_retriever() -> object:
        raise MissingOpenAIKeyError("OPENAI_API_KEY no está configurada.")

    monkeypatch.setattr(main, "get_retriever", missing_retriever)

    with TestClient(main.app) as client:
        response = client.post("/api/chat", json={"message": "Necesito una patente"})

    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]
