"""Pure validation for uploaded and camera-captured image bytes."""

import hashlib
import warnings
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

FORMAT_DETAILS = {
    "JPEG": ("image/jpeg", "jpg"),
    "PNG": ("image/png", "png"),
    "WEBP": ("image/webp", "webp"),
}


class ImageValidationError(ValueError):
    """Raised when uploaded bytes do not satisfy the WUE image contract."""


class ImageSizeLimitError(ImageValidationError):
    """Raised when encoded bytes or decoded pixels exceed configured limits."""


@dataclass(frozen=True, slots=True)
class ValidatedImage:
    data: bytes
    content_type: str
    extension: str
    file_size_bytes: int
    checksum_sha256: str
    pixel_width: int
    pixel_height: int


def safe_original_filename(filename: str | None) -> str:
    """Keep display metadata only; never use a client path as a storage path."""
    if not filename:
        return "image"
    basename = Path(filename.replace("\\", "/")).name.strip()
    return (basename or "image")[:255]


def validate_image(
    data: bytes,
    declared_content_type: str | None,
    *,
    max_bytes: int,
    max_pixels: int,
) -> ValidatedImage:
    """Validate encoded type, decoded format, dimensions, and size limits."""
    if not data:
        raise ImageValidationError("Image content is empty")
    if len(data) > max_bytes:
        raise ImageSizeLimitError(
            f"Image exceeds the maximum size of {max_bytes} bytes"
        )
    if declared_content_type not in {details[0] for details in FORMAT_DETAILS.values()}:
        raise ImageValidationError("Only JPEG, PNG, and WebP images are supported")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                detected_format = image.format
                width, height = image.size
                if width * height > max_pixels:
                    raise ImageSizeLimitError(
                        f"Image exceeds the maximum pixel count of {max_pixels}"
                    )
                image.verify()
    except ImageSizeLimitError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageSizeLimitError("Image dimensions exceed the safe decoding limit") from exc
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise ImageValidationError("File content is not a valid image") from exc

    if detected_format not in FORMAT_DETAILS:
        raise ImageValidationError("Only JPEG, PNG, and WebP images are supported")
    detected_content_type, extension = FORMAT_DETAILS[detected_format]
    if declared_content_type != detected_content_type:
        raise ImageValidationError(
            "Declared content type does not match the detected image format"
        )

    return ValidatedImage(
        data=data,
        content_type=detected_content_type,
        extension=extension,
        file_size_bytes=len(data),
        checksum_sha256=hashlib.sha256(data).hexdigest(),
        pixel_width=width,
        pixel_height=height,
    )
