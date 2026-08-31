"""Closed domain value sets shared across application layers."""

from enum import Enum


class FurnitureType(str, Enum):
    """Furniture types supported by the complete WUE system."""

    CHAIR = "chair"
    DINING_TABLE = "dining_table"
    BOOKSHELF = "bookshelf"


class FurnitureImageView(str, Enum):
    """Required photographic views for each furniture item."""

    FRONT = "front"
    BACK = "back"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"


class ImageInputSource(str, Enum):
    """How image bytes entered WUE."""

    UPLOAD = "upload"
    CAMERA_CAPTURE = "camera_capture"
