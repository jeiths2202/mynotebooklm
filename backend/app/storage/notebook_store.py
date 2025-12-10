import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.models import Notebook, Document


class NotebookStore:
    """JSON-based storage for notebooks and documents metadata"""

    def __init__(self):
        self.file_path = settings.notebooks_file
        self._ensure_file()

    def _ensure_file(self) -> None:
        """Ensure the JSON file exists"""
        if not self.file_path.exists():
            self._save_data({"notebooks": {}, "documents": {}})

    def _load_data(self) -> Dict[str, Any]:
        """Load data from JSON file"""
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_data(self, data: Dict[str, Any]) -> None:
        """Save data to JSON file"""
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    # Notebook operations
    def create_notebook(self, notebook: Notebook) -> Notebook:
        """Create a new notebook"""
        data = self._load_data()
        data["notebooks"][notebook.id] = notebook.model_dump()
        self._save_data(data)
        return notebook

    def get_notebook(self, notebook_id: str) -> Optional[Notebook]:
        """Get a notebook by ID"""
        data = self._load_data()
        notebook_data = data["notebooks"].get(notebook_id)
        if notebook_data:
            return Notebook(**notebook_data)
        return None

    def list_notebooks(self) -> List[Notebook]:
        """List all notebooks"""
        data = self._load_data()
        notebooks = []
        for nb_data in data["notebooks"].values():
            notebook = Notebook(**nb_data)
            # Count documents for this notebook
            doc_count = sum(
                1 for doc in data["documents"].values()
                if doc["notebook_id"] == notebook.id
            )
            notebook.document_count = doc_count
            notebooks.append(notebook)
        return sorted(notebooks, key=lambda x: x.created_at, reverse=True)

    def delete_notebook(self, notebook_id: str) -> bool:
        """Delete a notebook and its documents"""
        data = self._load_data()
        if notebook_id not in data["notebooks"]:
            return False

        # Delete notebook
        del data["notebooks"][notebook_id]

        # Delete all documents for this notebook
        data["documents"] = {
            doc_id: doc for doc_id, doc in data["documents"].items()
            if doc["notebook_id"] != notebook_id
        }

        self._save_data(data)
        return True

    def update_notebook(self, notebook_id: str, name: str) -> Optional[Notebook]:
        """Update notebook name"""
        data = self._load_data()
        if notebook_id not in data["notebooks"]:
            return None

        data["notebooks"][notebook_id]["name"] = name
        self._save_data(data)
        return Notebook(**data["notebooks"][notebook_id])

    # Document operations
    def create_document(self, document: Document) -> Document:
        """Create a new document"""
        data = self._load_data()
        data["documents"][document.id] = document.model_dump()
        self._save_data(data)
        return document

    def get_document(self, document_id: str) -> Optional[Document]:
        """Get a document by ID"""
        data = self._load_data()
        doc_data = data["documents"].get(document_id)
        if doc_data:
            return Document(**doc_data)
        return None

    def list_documents(self, notebook_id: str) -> List[Document]:
        """List all documents for a notebook"""
        data = self._load_data()
        documents = [
            Document(**doc_data)
            for doc_data in data["documents"].values()
            if doc_data["notebook_id"] == notebook_id
        ]
        return sorted(documents, key=lambda x: x.uploaded_at, reverse=True)

    def delete_document(self, document_id: str) -> Optional[Document]:
        """Delete a document"""
        data = self._load_data()
        if document_id not in data["documents"]:
            return None

        document = Document(**data["documents"][document_id])
        del data["documents"][document_id]
        self._save_data(data)
        return document

    def update_document_chunks(self, document_id: str, chunk_count: int) -> None:
        """Update the chunk count for a document"""
        data = self._load_data()
        if document_id in data["documents"]:
            data["documents"][document_id]["chunk_count"] = chunk_count
            self._save_data(data)
