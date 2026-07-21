"""API HTTP del MVP PortoAsiste IA."""

import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.chains.chat_chain import ChatChainError, get_chat_chain, select_tramite
from app.core.config import get_settings
from app.db.database import get_db, init_db
from app.db.models import ChatHistory
from app.rag.knowledge_base import find_tramite, load_tramites
from app.rag.vector_store import MissingOpenAIKeyError, get_retriever
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.pdf_generator import generate_application_pdf

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Crea la tabla de historial y los directorios de trabajo al iniciar."""
    settings.ensure_runtime_directories()
    init_db()
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


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """Responde una consulta usando solo los trámites recuperados del RAG."""
    session_id = request.session_id or str(uuid4())

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
            "Actualmente solo puedo orientar sobre Permiso de Funcionamiento, "
            "Patente Municipal y Certificado de Uso de Suelo del GAD de Portoviejo. "
            "La consulta no corresponde a uno de esos trámites disponibles."
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

    try:
        db.add(
            ChatHistory(
                session_id=session_id,
                user_message=request.message,
                assistant_response=response.response,
            )
        )
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        logger.exception("No fue posible guardar el historial de chat")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible guardar el historial de la consulta.",
        ) from error

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
