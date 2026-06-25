# RAG API

A self-contained **Retrieval-Augmented Generation** service: upload documents,
they get chunked, embedded, and stored in a vector store; then ask questions and
get answers grounded in those documents, with sources.

Built as a small, clean FastAPI app:

```
ingest → chunk → embed → store (Chroma) → retrieve → generate (Groq LLM)
```

## Architecture at a glance

```
rag/
├── app/
│   ├── main.py                  # FastAPI app + lifespan (builds state on startup)
│   ├── config.py                # Settings (env / .env), single source of truth
│   ├── state.py                 # Composition root — builds & wires everything once
│   ├── api/
│   │   ├── deps.py              # FastAPI dependency providers (read app.state)
│   │   └── routes.py           # router scaffold — endpoint handlers owned separately
│   ├── controllers/
│   │   ├── document_controller.py   # orchestrates ingestion
│   │   └── chat_controller.py       # orchestrates retrieve-then-generate
│   ├── services/
│   │   ├── embedding_service.py     # sentence-transformers (text → vectors)
│   │   ├── ingestion_service.py     # LangChain loaders + text splitter
│   │   ├── retrieval_service.py     # embed query, search store, format context
│   │   └── llm_service.py           # Groq via langchain-groq + prompt template
│   ├── vectorstores/
│   │   ├── base.py                  # BaseVectorStore interface + Chunk/RetrievedChunk
│   │   ├── chroma_store.py          # Chroma implementation (only file importing chromadb)
│   │   └── factory.py               # chooses the backend (Chroma today)
│   └── models/
│       └── schemas.py               # Pydantic request/response models
├── scripts/
│   └── ingest_folder.py             # bulk-ingest a folder from the CLI
├── tests/                           # pytest suite
├── data/                            # sample docs + (gitignored) chroma_db/
├── requirements.txt
├── .env.example
└── pytest.ini
```

### Key design points

- **Layered, one-way dependencies.** Routes → controllers → services →
  vector-store interface. Nothing outside `chroma_store.py` imports `chromadb`,
  so swapping the vector backend is a change in `factory.py` only.
- **`BaseVectorStore` is the key abstraction.** Controllers/services talk to the
  interface, never a concrete store.
- **Built once, at startup.** `state.build_app_state()` constructs the embedding
  model, vector store, LLM client, and controllers a single time in the FastAPI
  lifespan; handlers receive them via `Depends`. Importing the app is cheap (no
  model download at import time).
- **No metadata database.** The vector store is the source of truth for
  "what's ingested" — `GET /documents` aggregates that from chunk metadata.

## Quickstart

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt

cp .env.example .env            # then set GROQ_API_KEY

uvicorn app.main:app --reload --port 8000
```

The app boots and Swagger UI is served at **http://localhost:8000/docs** — but
it will list no routes yet (see "API — status" below; endpoint handlers are
owned separately).

> First startup downloads the `all-MiniLM-L6-v2` embedding model (~90 MB) from
> Hugging Face and caches it locally. Subsequent starts are fast.

## API — status: scaffold only

The HTTP **endpoint handlers are not implemented** (that work is owned
separately). What *is* in place and ready for them:

- `app/main.py` boots the app, builds all services once, and mounts the router
  under `/api/v1`.
- `app/api/routes.py` exposes a `router` ready for handlers (currently empty, so
  the app starts with no routes — `/docs` will show an empty API until they're
  added).
- `app/api/deps.py` provides `get_document_controller`, `get_chat_controller`,
  and `get_vector_store` for use with `Depends`.
- `app/models/schemas.py` defines the intended request/response models
  (`ChatRequest`/`ChatResponse`, `DocumentUploadResponse`,
  `DocumentListResponse`, `HealthResponse`, …).

The intended endpoint set and how data flows through each is documented in
[DATA_FLOW.md](DATA_FLOW.md). Until handlers exist, drive the pipeline directly
via the controllers (see below) or the bulk-ingest script.

## Bulk ingest (no HTTP)

```bash
python -m scripts.ingest_folder data
```

Ingests every supported file in the folder, assigning each its own `document_id`.

## Use the pipeline directly (no HTTP)

Until the endpoints exist, you can call the same logic the API would:

```python
from app.state import build_app_state

rag = build_app_state()  # builds embedding model, store, LLM, controllers once

rag.document_controller.ingest_document("data/mydoc.pdf", document_id="doc-1")
result = rag.chat_controller.answer("What is this document about?")
print(result["answer"])
print(result["sources"])
```

## Tests

```bash
pytest
```

- `test_ingestion.py`, `test_retrieval.py` run with fakes — no network needed.
- `test_embedding.py` loads the real embedding model and **skips** if it can't
  be downloaded/loaded (e.g. offline).

## Configuration

All settings live in `app/config.py` and are overridable via `.env` — see
`.env.example`. Notable ones: `CHUNK_SIZE`/`CHUNK_OVERLAP`, `RETRIEVAL_TOP_K`,
`EMBEDDING_MODEL_NAME`, `GROQ_MODEL_NAME`, `CHROMA_PERSIST_DIR`.

See [SETUP.md](SETUP.md) for a step-by-step setup and [DATA_FLOW.md](DATA_FLOW.md)
for how data moves through the system, file by file.
