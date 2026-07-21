"""Contrato exitoso de /api/chat sin proveedores externos ni persistencia real."""

from fastapi.testclient import TestClient

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

    def fake_get_db():
        yield database

    monkeypatch.setattr(main, "get_retriever", lambda: FakeRetriever())
    monkeypatch.setattr(main, "get_chat_chain", lambda: FakeChatService())
    main.app.dependency_overrides[main.get_db] = fake_get_db

    try:
        client = TestClient(main.app)
        response = client.post(
            "/api/chat",
            json={
                "message": "Necesito una patente municipal",
                "session_id": "contrato-frontend-123",
            },
        )
    finally:
        client.close()
        main.app.dependency_overrides.pop(main.get_db, None)

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
