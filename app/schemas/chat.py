"""Contratos Pydantic del endpoint de chat."""

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """Mensaje ciudadano y una sesión opcional sin autenticación."""

    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        """Evita llamadas de OpenAI para mensajes vacíos o solo espacios."""
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("message no puede estar vacío.")
        return cleaned_value


class ChatResponse(BaseModel):
    """Respuesta estructurada que consume el frontend."""

    response: str
    tramite_detectado: str | None = None
    requisitos: list[str] | None = None
    costo_estimado: str | None = None
    tiempo_estimado: str | None = None
    session_id: str
