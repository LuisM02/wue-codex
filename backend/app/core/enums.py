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


class DimensionUnit(str, Enum):
    """Units accepted at the overall-dimensions API boundary."""

    MILLIMETER = "mm"
    CENTIMETER = "cm"
    METER = "m"
    INCH = "in"


class DimensionSource(str, Enum):
    """Provenance of a furniture dimension set."""

    MANUAL = "manual"
    AI_ESTIMATE = "ai_estimate"


class PlanStatus(str, Enum):
    """Lifecycle states for a versioned parametric plan."""

    DRAFT = "draft"
    FINALIZED = "finalized"


class ComponentType(str, Enum):
    """Geometry primitives supported by WUE furniture plans."""

    PANEL = "panel"
    LEG = "leg"
