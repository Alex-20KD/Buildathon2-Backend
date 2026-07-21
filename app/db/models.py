"""Modelo único para guardar el historial simple de chat."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ChatHistory(Base):
    """Un intercambio ciudadano-asistente, asociado a un session_id sin usuarios."""

    __tablename__ = "chat_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(100), index=True)
    user_message: Mapped[str] = mapped_column(Text)
    assistant_response: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
