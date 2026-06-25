"""
Composition root.

Builds every service and controller once and wires them together. This is
the single place that knows how the pieces fit; everything else receives
already-constructed objects.

`build_app_state()` is called once at application startup (see
`app/main.py`'s lifespan handler) and the result is stored on
`app.state.rag`. Request handlers reach it through `app/api/deps.py`.

Constructing `AppState` loads the embedding model into memory and opens
the vector store, so it is deliberately NOT done at import time — only
when the app actually starts.
"""

from dataclasses import dataclass

from app.controllers.chat_controller import ChatController
from app.controllers.document_controller import DocumentController
from app.services.embedding_service import get_embedding_service
from app.services.ingestion_service import get_ingestion_service
from app.services.llm_service import get_llm_service
from app.services.retrieval_service import RetrievalService
from app.vectorstores.base import BaseVectorStore
from app.vectorstores.factory import get_vector_store_instance


@dataclass
class AppState:
    document_controller: DocumentController
    chat_controller: ChatController
    vector_store: BaseVectorStore


def build_app_state() -> AppState:
    embedding_service = get_embedding_service()
    ingestion_service = get_ingestion_service()
    llm_service = get_llm_service()
    vector_store = get_vector_store_instance()

    retrieval_service = RetrievalService(vector_store, embedding_service)

    document_controller = DocumentController(
        ingestion_service, embedding_service, vector_store
    )
    chat_controller = ChatController(retrieval_service, llm_service)

    return AppState(
        document_controller=document_controller,
        chat_controller=chat_controller,
        vector_store=vector_store,
    )
