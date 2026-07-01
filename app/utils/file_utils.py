from fastapi import UploadFile
import uuid
from pathlib import Path
from app.config import settings
from app.core.exceptions import UnsupportedFileTypeError, FileTooLargeError

def validate_extension(filename: str = ""):
    extension = Path(filename).suffix.lower()
    if extension not in settings.ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError(extension)
    return extension

async def save_upload(file: UploadFile, document_id: str|None = None):
    filename = file.filename
    extension = validate_extension(filename or "")
    document_id = document_id or str(uuid.uuid4())

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    dest_path = upload_dir / f"{document_id}{extension}"

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    size = 0

    with open(dest_path, "wb") as out_file:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                out_file.close()
                dest_path.unlink(missing_ok=True)
                raise FileTooLargeError(settings.MAX_UPLOAD_SIZE_MB)
            out_file.write(chunk)

    return str(dest_path), document_id, filename, extension