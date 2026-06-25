"""
Bulk-ingest every supported file in a folder into the vector store.

Useful for seeding the store outside the HTTP API (e.g. an initial corpus).
Each file gets its own generated `document_id`.

Usage:
    python -m scripts.ingest_folder <folder_path>

Example:
    python -m scripts.ingest_folder data
"""

import sys
import uuid
from pathlib import Path

from app.controllers.document_controller import DocumentController
from app.services.embedding_service import get_embedding_service
from app.services.ingestion_service import SUPPORTED_EXTENSIONS, get_ingestion_service
from app.vectorstores.factory import get_vector_store_instance


def ingest_folder(folder: str) -> None:
    folder_path = Path(folder)
    if not folder_path.is_dir():
        raise SystemExit(f"Not a directory: {folder}")

    controller = DocumentController(
        ingestion_service=get_ingestion_service(),
        embedding_service=get_embedding_service(),
        vector_store=get_vector_store_instance(),
    )

    total_files = 0
    total_chunks = 0
    for path in sorted(folder_path.iterdir()):
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        document_id = str(uuid.uuid4())
        try:
            count = controller.ingest_document(str(path), document_id)
        except Exception as exc:  # keep going if one file is bad
            print(f"  ! Skipped {path.name}: {exc}")
            continue
        total_files += 1
        total_chunks += count
        print(f"  + {path.name}: {count} chunks (document_id={document_id})")

    print(f"\nDone. Ingested {total_files} file(s), {total_chunks} chunk(s).")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m scripts.ingest_folder <folder_path>")
    ingest_folder(sys.argv[1])


if __name__ == "__main__":
    main()
