"""Contrato exitoso de /api/chat sin proveedores externos ni persistencia real."""

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app import main
from app.rag.vector_store import RetrievedTramite


class FakeDatabaseSession:
    """Reemplaza SQLite para que la prueba no escriba historial en disco."""

    def __init__(self) -> None:
        self.records: list[object] = []
        self.committed = False

    def add(self, record: object) -> None:
        self.records.append(record)

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass


def test_post_chat_returns_frontend_contract_with_mocked_services(monkeypatch) -> None:
    """El API expone todos los campos que consume el frontend sin usar OpenAI/FAISS."""
    tramite = RetrievedTramite(
        nombre="Patente Municipal",
        descripcion="Registro para ejercer una actividad econ\u00f3mica en el cant\u00f3n.",
        requisitos=["C\u00e9dula", "RUC"],
        costo_estimado="Seg\u00fan el aval\u00fao municipal.",
        tiempo_estimado="3 d\u00edas h\u00e1biles.",
        palabras_clave=["patente", "actividad econ\u00f3mica"],
    )
    database = FakeDatabaseSession()

    class FakeRetriever:
        def retrieve(self, query: str) -> list[RetrievedTramite]:
            assert query == "Necesito una patente municipal"
            return [tramite]

    class FakeChatService:
        def answer(
            self,
            message: str,
            selected_tramite: RetrievedTramite,
            retrieved_tramites: list[RetrievedTramite],
        ) -> str:
            assert message == "Necesito una patente municipal"
            assert selected_tramite is tramite
            assert retrieved_tramites == [tramite]
            return "Puedes iniciar tu solicitud de patente municipal con los requisitos indicados."

    monkeypatch.setattr(main, "get_retriever", lambda: FakeRetriever())
    monkeypatch.setattr(main, "get_chat_chain", lambda: FakeChatService())
    monkeypatch.setattr(main, "SessionLocal", lambda: database)

    with TestClient(main.app) as client:
        response = client.post(
            "/api/chat",
            json={
                "message": "Necesito una patente municipal",
                "session_id": "contrato-frontend-123",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "response": "Puedes iniciar tu solicitud de patente municipal con los requisitos indicados.",
        "tramite_detectado": "Patente Municipal",
        "requisitos": ["C\u00e9dula", "RUC"],
        "costo_estimado": "Seg\u00fan el aval\u00fao municipal.",
        "tiempo_estimado": "3 d\u00edas h\u00e1biles.",
        "session_id": "contrato-frontend-123",
    }
    assert database.committed
    assert len(database.records) == 1


def test_post_chat_returns_response_when_history_database_is_unavailable(monkeypatch) -> None:
    """El agente debe responder aunque no se pueda persistir el historial."""
    tramite = RetrievedTramite(
        nombre="Patente Municipal",
        descripcion="Registro para ejercer una actividad econ\u00f3mica en el cant\u00f3n.",
        requisitos=["C\u00e9dula"],
        costo_estimado="Seg\u00fan el aval\u00fao municipal.",
        tiempo_estimado="3 d\u00edas h\u00e1biles.",
        palabras_clave=["patente"],
    )

    class UnavailableDatabaseSession:
        def add(self, record: object) -> None:
            pass

        def commit(self) -> None:
            raise SQLAlchemyError("Base de datos no disponible")

        def rollback(self) -> None:
            pass

        def close(self) -> None:
            pass

    class FakeRetriever:
        def retrieve(self, query: str) -> list[RetrievedTramite]:
            return [tramite]

    class FakeChatService:
        def answer(self, **_: object) -> str:
            return "Respuesta generada por OpenAI."

    monkeypatch.setattr(main, "get_retriever", lambda: FakeRetriever())
    monkeypatch.setattr(main, "get_chat_chain", lambda: FakeChatService())
    monkeypatch.setattr(main, "SessionLocal", UnavailableDatabaseSession)

    with TestClient(main.app) as client:
        response = client.post("/api/chat", json={"message": "Necesito una patente"})

    assert response.status_code == 200
    assert response.json()["response"] == "Respuesta generada por OpenAI."
