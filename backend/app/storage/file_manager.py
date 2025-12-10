import shutil
from pathlib import Path
from typing import Optional
from fastapi import UploadFile

from app.config import settings


class FileManager:
    """Manages file uploads and storage"""

    ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

    def __init__(self):
        self.upload_dir = settings.upload_dir

    def get_notebook_dir(self, notebook_id: str) -> Path:
        """Get the upload directory for a notebook"""
        notebook_dir = self.upload_dir / notebook_id
        notebook_dir.mkdir(parents=True, exist_ok=True)
        return notebook_dir

    def validate_file(self, file: UploadFile) -> Optional[str]:
        """Validate uploaded file. Returns error message or None if valid."""
        if not file.filename:
            return "No filename provided"

        extension = Path(file.filename).suffix.lower()
        if extension not in self.ALLOWED_EXTENSIONS:
            return f"File type not allowed. Allowed types: {', '.join(self.ALLOWED_EXTENSIONS)}"

        # Validate file size
        if file.size and file.size > self.MAX_FILE_SIZE:
            max_mb = self.MAX_FILE_SIZE / (1024 * 1024)
            return f"File size exceeds {max_mb:.0f}MB limit"

        return None

    async def save_file(
        self,
        notebook_id: str,
        file: UploadFile,
        document_id: str
    ) -> Path:
        """Save uploaded file and return the path"""
        notebook_dir = self.get_notebook_dir(notebook_id)

        # Create unique filename with document_id
        original_name = Path(file.filename).stem
        extension = Path(file.filename).suffix.lower()
        filename = f"{document_id}_{original_name}{extension}"

        file_path = notebook_dir / filename

        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        return file_path

    def delete_file(self, file_path: Path) -> None:
        """Delete a file"""
        if file_path.exists():
            file_path.unlink()

    def delete_notebook_files(self, notebook_id: str) -> None:
        """Delete all files for a notebook"""
        notebook_dir = self.upload_dir / notebook_id
        if notebook_dir.exists():
            shutil.rmtree(notebook_dir)

    def get_file_path(self, notebook_id: str, document_id: str) -> Optional[Path]:
        """Find file path for a document"""
        notebook_dir = self.upload_dir / notebook_id
        if not notebook_dir.exists():
            return None

        for file_path in notebook_dir.iterdir():
            if file_path.name.startswith(document_id):
                return file_path

        return None
