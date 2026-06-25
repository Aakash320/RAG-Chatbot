from app.api.deps import get_vector_store
from app.vectorstores.base import BaseVectorStore
from fastapi import APIRouter, Depends, UploadFile, File
from app.utils.file_utils import save_upload
from app.api.deps import get_document_controller
from app.controllers.document_controller import DocumentController
from typing import Annotated
from app.models.schemas import DocumentUploadResponse, DocumentListResponse, DocumentMetadata, DocumentDeleteResponse
from pathlib import Path

router = APIRouter(prefix="/documents", tags=["documents"])



@router.post("", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    file: UploadFile,
    controller: Annotated[DocumentController, Depends(get_document_controller)],
) -> DocumentUploadResponse:
    document_id, file_path = await save_upload(file)

    try:
        chunk_count = controller.ingest_document(file_path=file_path, document_id=document_id)
    finally:
        Path(file_path).unlink(missing_ok=True)

    return DocumentUploadResponse(
        document_id=document_id,
        filename=file.filename or document_id,
        chunk_count=chunk_count,
        status="ingested",
    )


@router.get("", response_model = DocumentListResponse)
def list_documents(
    vector_store: Annotated[BaseVectorStore, Depends(get_vector_store)]
) -> DocumentListResponse:
    docs = vector_store.list_documents()
    return DocumentListResponse(
        documents = [DocumentMetadata(**d) for d in docs],
        total = len(docs),
    )

@router.delete("/{document_id}", response_model = DocumentDeleteResponse)
def delete_document(
    document_id: str,
    controller: Annotated[DocumentController, Depends(get_document_controller)]
) -> DocumentDeleteResponse:
    controller.delete_document(document_id)
    return DocumentDeleteResponse(
        document_id= document_id,
        deleted = True,
    )