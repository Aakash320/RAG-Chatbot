"""
Custom exceptions + FastAPI exception handlers.

Controllers/services raise these instead of generic Exceptions, so the
API returns clean, predictable JSON error bodies instead of leaking
stack traces.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class AppError(Exception):
    """Base class for all application-specific errors."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class DocumentNotFoundError(AppError):
    def __init__(self, document_id: str) -> None:
        super().__init__(f"Document '{document_id}' not found", status_code=404)


class UnsupportedFileTypeError(AppError):
    def __init__(self, extension: str) -> None:
        super().__init__(f"Unsupported file type: '{extension}'", status_code=415)


class FileTooLargeError(AppError):
    def __init__(self, max_size_mb: int) -> None:
        super().__init__(f"File exceeds max upload size of {max_size_mb}MB", status_code=413)


class IngestionError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"Ingestion failed: {detail}", status_code=500)


class LLMGenerationError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"LLM generation failed: {detail}", status_code=502)


class VectorStoreError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"Vector store operation failed: {detail}", status_code=500)


class RetrievalError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"Retrieval failed: {detail}", status_code=500)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
