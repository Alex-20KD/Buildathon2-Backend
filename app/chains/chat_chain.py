"""Cadena de chat estricta para responder solo con el contexto RAG."""

from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import get_settings
from app.rag.knowledge_base import normalize_text
from app.rag.vector_store import MissingOpenAIKeyError, RetrievedTramite

SYSTEM_PROMPT = """
Eres PortoAsiste IA, asesor únicamente de trámites municipales del GAD de Portoviejo.
Responde exclusivamente con la información del CONTEXTO RECUPERADO. Nunca inventes
requisitos, costos, tiempos ni otros trámites. Si el contexto no permite responder,
indícalo de manera explícita. Escribe en español, con un tono formal y cercano.

Organiza siempre tu respuesta con estos encabezados:
Trámite identificado, Requisitos, Costo estimado y Tiempo estimado.

Cuando la consulta trate de abrir un negocio o vender alimentos, explica que el
Permiso de Funcionamiento requiere validar el Certificado de Uso de Suelo cuando
corresponda. Si la actividad no es compatible con el predio indicado, agrega el
encabezado "Alternativas si no es compatible". Indica que no debe operar allí
con esa actividad y que puede consultar al municipio por otro predio o una
actividad compatible. No inventes zonas, direcciones, actividades permitidas ni
autorizaciones que no consten en el contexto.
""".strip()


class ChatChainError(RuntimeError):
    """Representa un fallo al consultar el modelo de lenguaje."""


class ChatChain:
    """Pequeña cadena LangChain que recibe contexto ya recuperado."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise MissingOpenAIKeyError("OPENAI_API_KEY no está configurada.")
        self._chat_model = ChatOpenAI(
            model=settings.openai_chat_model,
            temperature=0,
            api_key=settings.openai_api_key,
        )

    def answer(
        self,
        message: str,
        selected_tramite: RetrievedTramite,
        retrieved_tramites: list[RetrievedTramite],
    ) -> str:
        """Invoca gpt-4o-mini con el resultado RAG limitado a los tres trámites."""
        context = "\n\n".join(item.as_context() for item in retrieved_tramites)
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"CONSULTA CIUDADANA:\n{message}\n\n"
                    f"TRÁMITE SELECCIONADO:\n{selected_tramite.as_context()}\n\n"
                    f"CONTEXTO RECUPERADO:\n{context}"
                )
            ),
        ]
        try:
            result = self._chat_model.invoke(messages)
        except Exception as error:  # El SDK expone varios tipos de errores de red/proveedor.
            raise ChatChainError("La consulta al modelo de OpenAI falló.") from error

        if not isinstance(result.content, str) or not result.content.strip():
            raise ChatChainError("OpenAI no devolvió una respuesta de texto válida.")
        return result.content.strip()


def select_tramite(
    message: str,
    retrieved_tramites: list[RetrievedTramite],
) -> RetrievedTramite | None:
    """Evita responder a temas ajenos aunque FAISS siempre devuelva vecinos."""
    normalized_message = normalize_text(message)
    for tramite in retrieved_tramites:
        terms = [tramite.nombre, *tramite.palabras_clave]
        if any(normalize_text(term) in normalized_message for term in terms):
            return tramite

    # Algunas consultas ciudadanas describen el negocio sin nombrar el trámite.
    # Se las asocia al permiso de funcionamiento, que es el punto de partida para
    # operar un establecimiento; el modelo después orienta sobre uso de suelo.
    business_intent_terms = (
        "vender",
        "venta",
        "negocio",
        "local",
        "comida",
        "alimentos",
        "encebollado",
        "hamburguesa",
        "hambuerguesa",
        "puesto",
        "carreta",
        "hot dog",
        "hotdog",
        "emprendimiento",
    )
    if any(term in normalized_message for term in business_intent_terms):
        return next(
            (
                tramite
                for tramite in retrieved_tramites
                if normalize_text(tramite.nombre) == "permiso de funcionamiento"
            ),
            None,
        )
    return None


def get_casual_response(message: str) -> str | None:
    """Responde saludos breves sin enviarlos al flujo de trámites."""
    normalized_message = normalize_text(message).strip(" ¡!¿?.,")

    if normalized_message in {"hola", "buenos dias", "buenas tardes", "buenas noches"}:
        return (
            "¡Hola! Soy PortoAsiste IA. Puedo orientarte sobre Permiso de "
            "Funcionamiento, Patente Municipal y Certificado de Uso de Suelo "
            "en Portoviejo. ¿Qué negocio o trámite deseas realizar?"
        )

    if "que haces" in normalized_message or "quien eres" in normalized_message:
        return (
            "Soy PortoAsiste IA, tu asistente para orientarte sobre trámites "
            "municipales en Portoviejo. Puedo ayudarte a identificar qué "
            "necesitas para abrir un negocio, obtener una patente o verificar "
            "el uso de suelo."
        )

    if normalized_message in {"gracias", "muchas gracias"}:
        return "¡Con gusto! Si tienes otra consulta sobre tu negocio o trámite, aquí estoy para ayudarte."

    return None


@lru_cache(maxsize=1)
def get_chat_chain() -> ChatChain:
    """Cachea el cliente de LangChain durante la vida del proceso."""
    return ChatChain()
