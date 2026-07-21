"""Paquete principal y punto de entrada ASGI de PortoAsiste IA."""

# Conserva compatibilidad con el comando previo de Render: ``gunicorn app:app``.
from app.main import app

__all__ = ["app"]
