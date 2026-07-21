# PortoAsiste IA - Backend

MVP de FastAPI para orientar sobre tres trámites del GAD Municipal de Portoviejo:
Permiso de Funcionamiento, Patente Municipal y Certificado de Uso de Suelo. Usa RAG con
LangChain, OpenAI Embeddings y FAISS; SQLite o PostgreSQL de Supabase guardan el historial
de chat.

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

## Usar Supabase como base de datos

El backend se conecta directamente a PostgreSQL; no expone credenciales de base de datos al
frontend. En `Buildathon2-Backend/.env`, reemplaza `DATABASE_URL` por la siguiente URL y
sustituye `TU_CONTRASENA` por la contraseña de la base de datos de Supabase:

```env
DATABASE_URL=postgresql://postgres:TU_CONTRASENA@db.lrhpnfcroynmaepxoglz.supabase.co:5432/postgres
```

La aplicación añade automáticamente SSL y crea `chat_history` al iniciarse. Si la contraseña
incluye caracteres como `@`, `:`, `/`, `?`, `#` o `%`, debes codificarla para una URL (por
ejemplo, `@` pasa a ser `%40`). La contraseña solo debe estar en `.env`, que Git ignora.

La primera llamada a `POST /api/chat` construye `faiss_index/` usando
`text-embedding-3-small`; las siguientes reutilizan ese índice. El servidor y el endpoint
`/health` pueden arrancar sin la clave, pero `/api/chat` responderá `503` hasta configurarla.

## Conectar el frontend

El frontend Vite se comunica con esta API mediante `POST /api/chat`. Para desarrollo local:

```env
# Buildathon2-Backend/.env
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://buildathon2-frontend.vercel.app
```

En `Buildathon2-Frontend/.env.local`, configura:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

En producción, configura `CORS_ORIGINS` como variable de entorno en el servicio del backend e incluye el dominio exacto del frontend publicado. Para la instancia actual es `https://buildathon2-frontend.vercel.app`. No uses `*` mientras `CORS_ORIGINS` se mantenga restringido. Después de guardarla, reinicia o vuelve a desplegar el backend.

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
