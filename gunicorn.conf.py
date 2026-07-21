"""Configuración compatible con el comando histórico `gunicorn app:app`.

Render debe iniciar la API con el comando definido en el Procfile. Esta configuración
mantiene la API disponible si el panel de Render conserva el comando anterior.
"""

import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
worker_class = "uvicorn.workers.UvicornWorker"
workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
