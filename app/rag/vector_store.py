"""Índice FAISS persistente y el puerto mínimo del recuperador RAG."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.core.config import Settings, get_settings
from app.rag.knowledge_base import Tramite, load_tramites


class MissingOpenAIKeyError(RuntimeError):
    """Se lanza cuando una operación RAG necesita una clave ausente."""


class BaseRetriever(ABC):
    """Puerto mínimo para cambiar FAISS sin afectar la lógica de chat."""

    @abstractmethod
    def retrieve(self, query: str) -> list["RetrievedTramite"]:
        """Devuelve los trámites más relevantes para una consulta."""


@dataclass(frozen=True)
class RetrievedTramite:
    """Trámite recuperado junto con los campos que puede devolver la API."""

    nombre: str
    descripcion: str
    requisitos: list[str]
    costo_estimado: str
    tiempo_estimado: str
    palabras_clave: list[str]

    @classmethod
    def from_document(cls, document: Document) -> "RetrievedTramite":
        """Restaura un trámite desde los metadatos guardados en FAISS."""
        metadata = document.metadata
        requirements = metadata["requisitos"]
        keywords = metadata["palabras_clave"]
        if not isinstance(requirements, list) or not isinstance(keywords, list):
            raise ValueError("Los metadatos de FAISS tienen un formato no válido.")
        return cls(
            nombre=str(metadata["nombre"]),
            descripcion=str(metadata["descripcion"]),
            requisitos=[str(item) for item in requirements],
            costo_estimado=str(metadata["costo_estimado"]),
            tiempo_estimado=str(metadata["tiempo_estimado"]),
            palabras_clave=[str(item) for item in keywords],
        )

    def as_context(self) -> str:
        """Crea contexto textual para el prompt sin datos ajenos al JSON."""
        requirements = "\n".join(f"- {requirement}" for requirement in self.requisitos)
        return (
            f"Trámite: {self.nombre}\n"
            f"Descripción: {self.descripcion}\n"
            f"Requisitos:\n{requirements}\n"
            f"Costo estimado: {self.costo_estimado}\n"
            f"Tiempo estimado: {self.tiempo_estimado}"
        )


class FaissRetriever(BaseRetriever):
    """Implementación local del puerto usando FAISS y OpenAI Embeddings."""

    def __init__(self, vector_store: FAISS, top_k: int = 3) -> None:
        self._vector_store = vector_store
        self._top_k = top_k

    def retrieve(self, query: str) -> list[RetrievedTramite]:
        documents = self._vector_store.similarity_search(query, k=self._top_k)
        return [RetrievedTramite.from_document(document) for document in documents]


def _documents_from_tramites(tramites: list[Tramite]) -> list[Document]:
    """Convierte los tres trámites en documentos enriquecidos para FAISS."""
    return [
        Document(
            page_content=tramite.as_context(),
            metadata={
                "nombre": tramite.nombre,
                "descripcion": tramite.descripcion,
                "requisitos": tramite.requisitos,
                "costo_estimado": tramite.costo_estimado,
                "tiempo_estimado": tramite.tiempo_estimado,
                "palabras_clave": tramite.palabras_clave,
            },
        )
        for tramite in tramites
    ]


def build_or_load_retriever(settings: Settings) -> BaseRetriever:
    """Carga FAISS existente o lo construye la primera vez que se usa el chat."""
    if not settings.openai_api_key:
        raise MissingOpenAIKeyError("OPENAI_API_KEY no está configurada.")

    settings.ensure_runtime_directories()
    embeddings = OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        api_key=settings.openai_api_key,
    )
    index_file = settings.faiss_index_dir / "index.faiss"
    metadata_file = settings.faiss_index_dir / "index.pkl"

    if index_file.exists() and metadata_file.exists():
        vector_store = FAISS.load_local(
            str(settings.faiss_index_dir),
            embeddings,
            allow_dangerous_deserialization=True,
        )
    else:
        vector_store = FAISS.from_documents(_documents_from_tramites(load_tramites()), embeddings)
        vector_store.save_local(str(settings.faiss_index_dir))

    return FaissRetriever(vector_store)


@lru_cache(maxsize=1)
def get_retriever() -> BaseRetriever:
    """Cachea el índice durante la vida del proceso web."""
    return build_or_load_retriever(get_settings())
