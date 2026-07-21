# PortoAsiste IA - Backend

MVP de FastAPI para orientar sobre tres trámites del GAD Municipal de Portoviejo:
Permiso de Funcionamiento, Patente Municipal y Certificado de Uso de Suelo. Usa RAG con
LangChain, OpenAI Embeddings y FAISS; SQLite guarda únicamente el historial de chat.

## Levantar en Fedora

```bash
sudo dnf install python3.12 python3.12-devel gcc gcc-c++ make libgomp
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
cp .env.example .env
```

Edita `.env` y define `OPENAI_API_KEY`. Puedes dejar los demás valores como están para
desarrollo local. Luego inicia la API desde la raíz del repositorio:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

La primera llamada a `POST /api/chat` construye `faiss_index/` usando
`text-embedding-3-small`; las siguientes reutilizan ese índice. El servidor y el endpoint
`/health` pueden arrancar sin la clave, pero `/api/chat` responderá `503` hasta configurarla.

## Probar

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Quiero abrir un restaurante"}'

curl -G http://localhost:8000/api/tramites/generar \
  --data-urlencode 'tramite=Permiso de Funcionamiento' \
  --data-urlencode 'nombre_solicitante=Ana Pérez' \
  --output solicitud.pdf
```

La documentación interactiva queda disponible en `http://localhost:8000/docs`.
