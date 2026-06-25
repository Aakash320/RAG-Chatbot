# Setup Guide — RAG API

Step-by-step to get the service running locally.

---

## 1. Prerequisites

- Python 3.11 or 3.12
- A [Groq API key](https://console.groq.com/keys) (free tier available) — only
  needed for `/chat`; ingestion works without it.

No database server and no Docker required — Chroma persists to a local folder.

---

## 2. Install dependencies

From the project root:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

> If `pip install` fails with `OSError: No space left on device`, that's disk
> space on your machine — free some up and retry with
> `pip install --no-cache-dir -r requirements.txt`.

---

## 3. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and set your Groq key:

```env
GROQ_API_KEY=your_actual_groq_api_key
```

Everything else has working defaults (chunk size 1000, overlap 200, top_k 4,
embedding model `all-MiniLM-L6-v2`, Chroma persisting to `data/chroma_db/`).

---

## 4. Run the app

```bash
uvicorn app.main:app --reload --port 8000
```

- Swagger UI: http://localhost:8000/docs

> **Note:** the HTTP endpoints are not implemented yet (that work is owned
> separately — see "API — status" in the README), so `/docs` will list no routes
> until they're added. The app, services, and dependency wiring still start up
> correctly.

**The first startup pauses** while `sentence-transformers` downloads the
`all-MiniLM-L6-v2` model (~90 MB) from Hugging Face; it's cached afterward.

---

## 5. Smoke test (without endpoints)

Drive the pipeline directly through the controllers:

```python
# smoke.py
from app.state import build_app_state

rag = build_app_state()
n = rag.document_controller.ingest_document(
    "data/6TH-Sem-Curriculum-and-Syllabus-1-1 (1).pdf", document_id="doc-1"
)
print(f"Ingested {n} chunks; store now holds {rag.vector_store.count()}.")

result = rag.chat_controller.answer("What subjects are in this curriculum?")
print(result["answer"])
```

```bash
python smoke.py
```

Or seed the store with the bulk-ingest script (next section).

---

## 6. What gets created on disk

```
data/
└── chroma_db/        # Chroma's persistent storage — embeddings + chunk text + metadata
```

This is what makes data durable across restarts. Delete it any time to start
with a clean, empty vector store. It is gitignored.

---

## 7. Bulk ingest from the CLI

To seed the store without going through HTTP:

```bash
python -m scripts.ingest_folder data
```

---

## 8. Run the tests

```bash
pytest
```

See the README for which tests need the model/deps and which run with fakes.

---

## 9. Common issues

| Symptom | Likely cause | Fix |
|---|---|---|
| First ingest / startup hangs | Downloading the embedding model from Hugging Face | Normal on first run only — needs internet once, then cached |
| `GROQ_API_KEY` errors when answering | Missing/invalid key in `.env` | Get a key from console.groq.com and set it |
| `ValueError: No content could be extracted` | Empty or corrupted document | Check the file isn't empty / isn't corrupted |
| `ValueError: Unsupported file extension` | Extension not supported | Use `.pdf`, `.docx`, `.txt`, or `.md` (add loaders in `app/services/ingestion_service.py`) |
| `Failed to send telemetry event` warnings from chromadb | Harmless chromadb/posthog quirk | Safe to ignore |
| Answers ignore your docs | Store empty, or `document_id` filter excludes everything | Check `vector_store.count()`; confirm you ingested first |
