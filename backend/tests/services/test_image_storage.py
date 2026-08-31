"""Focused tests for local image storage safety and lifecycle."""

from pathlib import Path

import pytest

from app.services.image_storage import ImageStorageNotFoundError, LocalImageStorage


def test_local_storage_round_trip(tmp_path: Path) -> None:
    storage = LocalImageStorage(tmp_path / "images")
    key = "furniture/front/example.png"

    storage.save(key, b"image-bytes")

    assert storage.read(key) == b"image-bytes"
    storage.delete(key)
    with pytest.raises(ImageStorageNotFoundError):
        storage.read(key)


def test_local_storage_rejects_keys_outside_root(tmp_path: Path) -> None:
    storage = LocalImageStorage(tmp_path / "images")

    with pytest.raises(ValueError, match="escapes"):
        storage.save("../outside.png", b"unsafe")
