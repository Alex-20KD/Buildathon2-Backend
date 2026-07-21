"""Pruebas del contrato de chat sin llamar a servicios externos."""

from fastapi.testclient import TestClient
from sqlalchemy import select

from app import main
from app.chains.chat_chain import get_casual_response, select_tramite
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


def test_select_tramite_recognizes_a_food_sales_business_intent() -> None:
    selected = select_tramite(
        "Quisiera vender hotdogs y no sé qué hacer",
        [_retrieved_tramite()],
    )

    assert selected is not None
    assert selected.nombre == "Permiso de Funcionamiento"


def test_select_tramite_recognizes_a_food_business_by_its_name() -> None:
    selected = select_tramite(
        "Quisiera poner un local de encebollado en la playa",
        [_retrieved_tramite()],
    )

    assert selected is not None
    assert selected.nombre == "Permiso de Funcionamiento"


def test_casual_responses_are_natural_and_do_not_require_a_tramite() -> None:
    greeting = get_casual_response("Hola")
    purpose = get_casual_response("¿Qué haces?")

    assert greeting is not None
    assert "¡Hola!" in greeting
    assert purpose is not None
    assert "Soy PortoAsiste IA" in purpose
