# Data Flow & File Reference — RAG API

What each file does, and exactly how data moves through the system for the two
things this service does: **storing a document** and **answering a question**.

> **Note:** the HTTP **endpoint handlers are not implemented yet** (owned
> separately). The `POST /api/v1/...` entry points shown in sections 4–5 are the
> *intended* API surface; today the controllers are the entry point (see the
> README's "Use the pipeline directly"). Everything from the controllers down is
> implemented and is what the endpoints will call.

---

## 1. Where are embeddings actually stored?

**On disk, in `data/chroma_db/`**, relative to where you run the app from
(configurable via `CHROMA_PERSIST_DIR`).

This is created and managed entirely by `ChromaVectorStore`
(`app/vectorstores/chroma_store.py`), which wraps a `chromadb.PersistentClient`.
Inside that folder, Chroma keeps, per chunk:

- the raw text
- the embedding vector (384 floats, from `all-MiniLM-L6-v2`)
- the metadata dict (`source_file`, `document_id`, `chunk_index`, `file_type`)

All of it lives in one Chroma **collection** (default name `documents`,
configurable via `CHROMA_COLLECTION_NAME`). There is **no separate metadata
database** — the collection is the single source of truth for what's stored,
and `GET /documents` aggregates that view directly from chunk metadata.

---

## 2. Layers, top to bottom

```
HTTP request
  → app/main.py            FastAPI app; builds AppState once in the lifespan
  → app/api/routes.py      router scaffold — endpoint handlers pending
  → app/api/deps.py        hands the endpoint the right controller/store
  → app/controllers/*      orchestrate the steps in order   ← entry point today
  → app/services/*         do one job each (embed / load+chunk / retrieve / LLM)
  → app/vectorstores/*     the storage abstraction + Chroma implementation
```

Dependencies point one way (down). Nothing low-level reaches back up.

---

## 3. File-by-file reference

### `app/config.py`
Reads settings from env / `.env`: embedding model, chunk size/overlap, top_k,
Chroma path & collection, Groq key/model/temperature/max_tokens, plus
app/API/CORS settings. Everything imports `settings` from here. Pure config.

### `app/main.py`
Creates the FastAPI app, adds CORS, includes the router under `/api/v1`. Its
**lifespan** handler calls `build_app_state()` once on startup and stashes the
result on `app.state.rag`. Importing this module does *not* load the model —
that happens at startup.

### `app/state.py`
The **composition root**. `build_app_state()` constructs each service and
controller once and wires them together into an `AppState`. The one place that
knows how the pieces fit.

### `app/api/deps.py`
FastAPI dependency providers. Each reads the relevant object
(`document_controller`, `chat_controller`, `vector_store`) off `app.state.rag`.
Endpoints declare these via `Depends`, which also makes them trivial to override
with fakes in tests.

### `app/api/routes.py`
Defines the `router` that `main.py` mounts under `/api/v1`. The endpoint
**handlers are not implemented yet** (owned separately) — the module is a
scaffold with guidance on how a handler plugs into the dependency providers.
When written, handlers should validate input, call a controller (or the store),
shape the result into a Pydantic response, translate controller exceptions
(e.g. `ValueError`) into HTTP errors, and be synchronous `def` so FastAPI runs
the blocking embedding/LLM work in a threadpool.

### `app/models/schemas.py`
Pydantic models describing the HTTP contract (`ChatRequest`, `ChatResponse`,
`DocumentUploadResponse`, `DocumentListResponse`, `DocumentMetadata`,
`HealthResponse`, …). Kept separate from the internal `Chunk`/`RetrievedChunk`
dataclasses so the wire format and internal shapes can drift independently.

### `app/vectorstores/base.py`
Defines the **shape** of data in/out of the store and the interface every
backend implements:
- `Chunk` — a piece of text *going in*: `id`, `text`, `metadata`.
- `RetrievedChunk` — a piece *coming back* from search: same fields plus `score`.
- `BaseVectorStore` — abstract methods `add_documents`, `similarity_search`,
  `delete`, `delete_by_metadata`, `count`, `list_documents`. A contract, no
  storage of its own.

### `app/vectorstores/chroma_store.py`
The only file that talks to Chroma directly:
- `add_documents()` → Chroma `upsert()` (same `id` overwrites, no duplicates).
- `similarity_search()` → Chroma `query()`, converting cosine distance (0–2) to
  a 0–1 similarity via `1 - (distance / 2)`.
- `delete_by_metadata()` → deletes every chunk matching a filter, e.g.
  `{"document_id": "abc"}` — how a whole document is removed.
- `count()` → total chunks stored.
- `list_documents()` → reads all chunk metadata and aggregates by `document_id`
  into `{document_id, filename, file_type, chunk_count}`.

### `app/vectorstores/factory.py`
`get_vector_store_instance()` — the single switch point for which backend is
used (Chroma today). Cached, so the whole app shares one store instance.

### `app/services/embedding_service.py`
Wraps `sentence-transformers`. Loads `all-MiniLM-L6-v2` once (cached) and exposes
`embed_texts(texts)` (batch, for ingestion) and `embed_query(text)` (one query).
Input: strings. Output: lists of 384 floats. Touches no storage.

### `app/services/ingestion_service.py`
Turns a file into `Chunk` objects:
- `load_file()` — picks a LangChain loader by extension (`PyPDFLoader`,
  `Docx2txtLoader`, `TextLoader`), extracts text, tags `source_file`/`file_type`.
- `chunk_documents()` — `RecursiveCharacterTextSplitter` (1000/200 default),
  wraps each piece as a `Chunk` with `document_id` and `chunk_index`.
- `load_and_chunk()` — both in one call (what the controller uses).
- `load_folder()` — bulk load (used by `scripts/ingest_folder.py`).
- `SUPPORTED_EXTENSIONS` — the one list of allowed types, reused by the API and
  the bulk-ingest script.

### `app/services/retrieval_service.py`
- `retrieve(query, top_k, document_id)` — embeds the query, calls the store's
  `similarity_search()`, optionally filtered to one `document_id`.
- `format_context(chunks)` — flattens retrieved chunks into one numbered,
  source-labeled text block for the prompt. Reads the store, never writes.

### `app/services/llm_service.py`
Wraps the Groq chat model via `langchain-groq`.
- `generate_answer(question, context)` — builds a `prompt | llm | parser` chain
  with a system prompt that says answer **only** from context (and admit when it
  doesn't know), returns plain text.
- `agenerate_answer(...)` — async equivalent. Makes a network call to Groq.

### `app/controllers/document_controller.py`
Orchestrates **ingestion**: `load_and_chunk` → `embed_texts` →
`vector_store.add_documents`. Also `delete_document(document_id)` →
`delete_by_metadata`. Raises `ValueError` if nothing could be extracted.

### `app/controllers/chat_controller.py`
Orchestrates **question answering**: `retrieve` → (short-circuit fallback if
nothing found) → `format_context` → `generate_answer` → package
`{answer, sources}`.

---

## 4. Full data flow — ingesting a document

```
   POST /api/v1/documents  (multipart file)
            │
            │  routes.upload_document: validate extension, save to a temp file,
            │  generate a document_id
            ▼
  DocumentController.ingest_document(tmp_path, document_id)
            │
            ├─► IngestionService.load_and_chunk(file_path, document_id)
            │       ├─ load_file(): pick loader by extension, extract raw text
            │       └─ chunk_documents(): split into ~1000-char overlapping
            │          pieces, wrap each as Chunk(id, text, metadata)
            │   returns: list[Chunk]   (text only — NOT embedded yet)
            │
            ├─► EmbeddingService.embed_texts([c.text for c in chunks])
            │   returns: list[list[float]]   (one 384-dim vector per chunk)
            │
            └─► vector_store.add_documents(chunks, embeddings)
                    └─ ChromaVectorStore upsert(): writes ids, vectors, text,
                       metadata into the `documents` collection on disk
            │
   routes returns DocumentUploadResponse {document_id, filename, chunk_count, status}
   (the temp file is deleted in a finally block — the durable copy is in Chroma)
```

---

## 5. Full data flow — answering a question

```
   POST /api/v1/chat  {query, document_id?, top_k?}
            ▼
  ChatController.answer(query, document_id, top_k)
            │
            ├─► RetrievalService.retrieve(query, top_k, document_id)
            │       ├─ EmbeddingService.embed_query(query) → one 384-dim vector
            │       └─ vector_store.similarity_search(vec, top_k, filter)
            │              └─ Chroma query(): top_k closest chunks + score each
            │   returns: list[RetrievedChunk]
            │
            │   (if empty → return fallback answer here and STOP; no LLM call)
            │
            ├─► RetrievalService.format_context(chunks) → one labeled string
            │
            ├─► LLMService.generate_answer(question, context)
            │       └─ prompt|llm|parser → Groq (llama-3.3-70b) → text
            │
            └─► package {answer, sources:[{text, source_file, score}, ...]}
            │
   routes returns ChatResponse
```

**Answering is read-only** against the store. Only ingestion writes data.

---

## 6. Where each data-shape changes hands

| Stage | Data shape | Lives in |
|---|---|---|
| Raw upload | bytes (PDF/DOCX/TXT/MD) | request body → temp file in `routes.upload_document` |
| After loading | LangChain `Document`s | memory, `ingestion_service.load_file()` |
| After chunking | `Chunk` objects | memory, `ingestion_service.chunk_documents()` |
| After embedding | `list[list[float]]` | memory, `embedding_service.embed_texts()` |
| After storing | rows in a Chroma collection | **persisted** at `data/chroma_db/` |
| Query | a string | request body |
| After query embedding | one `list[float]` | memory |
| After retrieval | `RetrievedChunk` objects | memory |
| After context formatting | one string | memory |
| After generation | a string (the answer) | memory |
| Final result | `ChatResponse` JSON | HTTP response |

Only the Chroma read/write touches disk for storage. Everything else is
in-memory and gone once the request returns.
