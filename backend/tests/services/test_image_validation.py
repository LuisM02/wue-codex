"""Pure tests for image-byte validation and filename safety."""

import hashlib
from collections.abc import Callable

import pytest

from app.services.image_validation import (
    ImageSizeLimitError,
    ImageValidationError,
    safe_original_filename,
    validate_image,
)


@pytest.mark.parametrize(
    ("image_format", "content_type", "extension"),
    [
        ("JPEG", "image/jpeg", "jpg"),
        ("PNG", "image/png", "png"),
        ("WEBP", "image/webp", "webp"),
    ],
)
def test_validates_supported_encoded_formats(
    image_bytes_factory: Callable[..., bytes],
    image_format: str,
    content_type: str,
    extension: str,
) -> None:
    data = image_bytes_factory(image_format, (8, 6))

    validated = validate_image(
        data,
        content_type,
        max_bytes=1_000_000,
        max_pixels=1_000,
    )

    assert validated.content_type == content_type
    assert validated.extension == extension
    assert validated.file_size_bytes == len(data)
    assert validated.checksum_sha256 == hashlib.sha256(data).hexdigest()
    assert (validated.pixel_width, validated.pixel_height) == (8, 6)


def test_rejects_mismatched_declared_type(
    image_bytes_factory: Callable[..., bytes],
) -> None:
    with pytest.raises(ImageValidationError, match="does not match"):
        validate_image(
            image_bytes_factory("PNG"),
            "image/jpeg",
            max_bytes=1_000_000,
            max_pixels=1_000,
        )


@pytest.mark.parametrize(
    ("data", "content_type"),
    [(b"", "image/png"), (b"not-an-image", "image/png"), (b"GIF89a", "image/gif")],
)
def test_rejects_empty_invalid_or_unsupported_content(
    data: bytes,
    content_type: str,
) -> None:
    with pytest.raises(ImageValidationError):
        validate_image(
            data,
            content_type,
            max_bytes=1_000_000,
            max_pixels=1_000,
        )


def test_enforces_encoded_and_decoded_size_limits(
    image_bytes_factory: Callable[..., bytes],
) -> None:
    data = image_bytes_factory("PNG", (4, 4))

    with pytest.raises(ImageSizeLimitError, match="maximum size"):
        validate_image(data, "image/png", max_bytes=len(data) - 1, max_pixels=100)
    with pytest.raises(ImageSizeLimitError, match="pixel count"):
        validate_image(data, "image/png", max_bytes=len(data), max_pixels=15)


def test_filename_is_display_metadata_not_a_client_path() -> None:
    assert safe_original_filename(r"C:\fake\path\chair.png") == "chair.png"
    assert safe_original_filename("../../bookshelf.webp") == "bookshelf.webp"
    assert safe_original_filename(None) == "image"
