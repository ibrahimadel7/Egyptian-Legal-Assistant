# Egyptian Legal Assistant — Connected App

This workspace combines the React/Vite frontend and FastAPI RAG backend. The frontend sends chat messages to the real RAG API; mock assistant replies have been removed from the chat flow.

## 1. Configure the backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your Groq key to `backend/.env`:

```dotenv
GROQ_API_KEY=your_real_key_here
```

The provided dataset is already in `backend/data/legal_dataset_decoded.jsonl`. Build the local Chroma index once:

```bash
python scripts/ingest.py --reset
```

Then start the API from the `backend` directory:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API health check: `http://127.0.0.1:8000/health`

## 2. Start the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL, normally `http://localhost:5173`. The Vite dev server proxies `/api/*` and `/health` to `http://127.0.0.1:8000`, so no browser CORS setup is needed in local development.

For a separately hosted backend, set `VITE_API_BASE_URL` in `frontend/.env` to the API base URL (for example `https://api.example.com/api/v1`) and set the backend `CORS_ORIGINS` to the exact frontend origin.

## 3. What is connected

- `POST /api/v1/chat` receives `{ "message": "...", "conversation_id": "optional" }`.
- The returned `conversation_id` is retained and sent on subsequent turns.
- Backend statuses (`answered`, `needs_clarification`) are rendered using the returned answer.
- Source cards are created only from actual API `sources`; no placeholder legal citation is fabricated.
- Questions with no sufficiently relevant dataset evidence are answered by the configured LLM without dataset sources, with a general-information disclaimer for legal questions.
- API errors are shown in the conversation instead of silently falling back to mock answers.
- The frontend uses the backend's `source_id`, law name, article/unit metadata, and excerpt.

## 4. Checks

Backend (from `backend/`):

```bash
pytest -q
```

Frontend (from `frontend/`):

```bash
npm test
npm run build
```

## Important legal/product limitation

This remains an experimental RAG system. The dataset's legal currentness and amendment status are not verified. Retrieval does not establish that a provision is currently in force. The UI therefore avoids claiming currentness and advises users to consult a qualified Egyptian lawyer for case-specific decisions.
