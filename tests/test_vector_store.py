"""Prueba del ciclo FAISS sin realizar llamadas a OpenAI."""

from langchain_core.embeddings import Embeddings

from app.core.config import Settings
from app.rag import vector_store


class DeterministicEmbeddings(Embeddings):
    """Embeddings de prueba que permiten construir y recargar FAISS localmente."""

    @staticmethod
    def _embed(text: str) -> list[float]:
        normalized_text = text.lower()
        return [
            float("funcionamiento" in normalized_text or "restaurante" in normalized_text),
            float("patente" in normalized_text),
            float("suelo" in normalized_text or "predio" in normalized_text),
        ]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def test_faiss_index_is_created_then_loaded_from_disk(monkeypatch, tmp_path) -> None:
    settings = Settings(
        openai_api_key="test-key",
        faiss_index_dir=tmp_path / "faiss_index",
        generated_pdfs_dir=tmp_path / "generated_pdfs",
    )
    monkeypatch.setattr(vector_store, "OpenAIEmbeddings", lambda **_: DeterministicEmbeddings())

    created_retriever = vector_store.build_or_load_retriever(settings)
    first_results = created_retriever.retrieve("Quiero abrir un restaurante")

    loaded_retriever = vector_store.build_or_load_retriever(settings)
    second_results = loaded_retriever.retrieve("Necesito revisar el uso de suelo")

    assert (settings.faiss_index_dir / "index.faiss").exists()
    assert (settings.faiss_index_dir / "index.pkl").exists()
    assert len(first_results) == 3
    assert len(second_results) == 3
