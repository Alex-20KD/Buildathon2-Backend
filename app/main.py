"""API HTTP del MVP PortoAsiste IA."""

import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError

from app.chains.chat_chain import (
    ChatChainError,
    get_casual_response,
    get_chat_chain,
    select_tramite,
)
from app.core.config import get_settings
from app.db.database import SessionLocal, init_db
from app.db.models import ChatHistory
from app.rag.knowledge_base import find_tramite, load_tramites
from app.rag.vector_store import MissingOpenAIKeyError, get_retriever
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.pdf_generator import generate_application_pdf

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Prepara directorios y el historial, sin bloquear el agente si la BD falla."""
    settings.ensure_runtime_directories()
    try:
        init_db()
    except SQLAlchemyError:
        app.state.history_enabled = False
        logger.exception("El historial no estÃ¡ disponible; el asistente continuarÃ¡ sin persistencia")
    else:
        app.state.history_enabled = True
    yield


app = FastAPI(
    title="PortoAsiste IA",
    version="0.1.0",
    description="Asistente de trámites municipales del GAD de Portoviejo.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health", include_in_schema=False)
def health_check() -> dict[str, str]:
    """Confirma que la API está disponible sin requerir la API de OpenAI."""
    return {"status": "ok"}


def persist_chat_history(session_id: str, user_message: str, assistant_response: str) -> None:
    """Guarda historial solo cuando la base estÃ¡ disponible, sin bloquear el agente."""
    if not getattr(app.state, "history_enabled", True):
        return

    database = None
    try:
        database = SessionLocal()
        database.add(
            ChatHistory(
                session_id=session_id,
                user_message=user_message,
                assistant_response=assistant_response,
            )
        )
        database.commit()
    except SQLAlchemyError:
        if database is not None:
            try:
                database.rollback()
            except SQLAlchemyError:
                pass
        app.state.history_enabled = False
        logger.exception("No fue posible guardar el historial; se entregarÃ¡ la respuesta del asistente")
    finally:
        if database is not None:
            database.close()


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Responde una consulta usando solo los trámites recuperados del RAG."""
    session_id = request.session_id or str(uuid4())
    casual_response = get_casual_response(request.message)

    if casual_response is not None:
        response = ChatResponse(response=casual_response, session_id=session_id)
    else:
        try:
            retrieved_tramites = get_retriever().retrieve(request.message)
        except MissingOpenAIKeyError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OPENAI_API_KEY no está configurada. Agrega la clave al archivo .env.",
            ) from error
        except Exception as error:  # pragma: no cover - protección ante proveedor externo
            logger.exception("No fue posible inicializar el índice FAISS")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No fue posible preparar la base de conocimiento. Intenta nuevamente.",
            ) from error

        tramite = select_tramite(request.message, retrieved_tramites)
        if tramite is None:
            assistant_response = (
                "Puedo orientarte sobre Permiso de Funcionamiento, Patente Municipal "
                "y Certificado de Uso de Suelo en Portoviejo. Cuéntame qué negocio "
                "deseas abrir o qué trámite necesitas realizar."
            )
            response = ChatResponse(response=assistant_response, session_id=session_id)
        else:
            try:
                assistant_response = get_chat_chain().answer(
                    message=request.message,
                    selected_tramite=tramite,
                    retrieved_tramites=retrieved_tramites,
                )
            except ChatChainError as error:
                logger.exception("La consulta a OpenAI no pudo completarse")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="No fue posible generar la respuesta del asistente. Intenta nuevamente.",
                ) from error

            response = ChatResponse(
                response=assistant_response,
                tramite_detectado=tramite.nombre,
                requisitos=tramite.requisitos,
                costo_estimado=tramite.costo_estimado,
                tiempo_estimado=tramite.tiempo_estimado,
                session_id=session_id,
            )

    persist_chat_history(
        session_id=session_id,
        user_message=request.message,
        assistant_response=response.response,
    )

    return response


@app.get("/api/tramites/generar")
def generate_tramite_pdf(
    tramite: str = Query(min_length=3, description="Nombre del trámite disponible"),
    nombre_solicitante: str = Query(min_length=2, max_length=120),
) -> FileResponse:
    """Genera una solicitud PDF sencilla para uno de los tres trámites permitidos."""
    selected_tramite = find_tramite(tramite, load_tramites())
    if selected_tramite is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trámite no disponible. Usa Permiso de Funcionamiento, Patente Municipal o "
            "Certificado de Uso de Suelo.",
        )

    pdf_path = generate_application_pdf(
        tramite=selected_tramite,
        applicant_name=nombre_solicitante,
        output_directory=settings.generated_pdfs_dir,
    )
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=pdf_path.name,
    )
