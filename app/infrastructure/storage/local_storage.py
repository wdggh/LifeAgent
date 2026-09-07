"""Local filesystem storage for uploaded files."""

import uuid
from pathlib import Path

from app.core.config import get_settings


class LocalFileStorage:
    """Store files under the configured upload directory.

    Files are stored under a generated name; the original filename is kept in
    the database only. The upload root is read from settings on every call so
    tests can redirect it to a temporary directory.
    """

    def _root(self) -> Path:
        return Path(get_settings().upload_dir)

    def save(self, original_filename: str, content: bytes) -> str:
        root = self._root()
        root.mkdir(parents=True, exist_ok=True)
        suffix = Path(original_filename).suffix.lower()
        stored_name = f"{uuid.uuid4().hex}{suffix}"
        (root / stored_name).write_bytes(content)
        return stored_name

    def delete(self, relative_path: str) -> None:
        # Defensive: only ever touch a bare filename inside the upload root.
        safe_name = Path(relative_path).name
        if not safe_name:
            return
        target = self._root() / safe_name
        if target.exists():
            target.unlink()

    def path_for(self, relative_path: str) -> Path:
        return self._root() / Path(relative_path).name
