"""Storage abstraction and local-filesystem implementation for image bytes."""

import os
from pathlib import Path
from typing import Protocol
from uuid import uuid4


class ImageStorageNotFoundError(FileNotFoundError):
    """Raised when metadata points to missing stored content."""


class ImageStorage(Protocol):
    def save(self, storage_key: str, data: bytes) -> None: ...

    def read(self, storage_key: str) -> bytes: ...

    def delete(self, storage_key: str) -> None: ...


class LocalImageStorage:
    """Atomic local storage whose generated keys stay beneath one root."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _path_for(self, storage_key: str) -> Path:
        candidate = (self.root / storage_key).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError("Storage key escapes the configured image directory")
        return candidate

    def save(self, storage_key: str, data: bytes) -> None:
        destination = self._path_for(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(
            f".{destination.name}.{uuid4().hex}.tmp"
        )
        try:
            temporary.write_bytes(data)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

    def read(self, storage_key: str) -> bytes:
        path = self._path_for(storage_key)
        try:
            return path.read_bytes()
        except FileNotFoundError as exc:
            raise ImageStorageNotFoundError(storage_key) from exc

    def delete(self, storage_key: str) -> None:
        self._path_for(storage_key).unlink(missing_ok=True)
