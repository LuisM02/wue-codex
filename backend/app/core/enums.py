"""Closed domain value sets shared across application layers."""

from enum import Enum


class FurnitureType(str, Enum):
    """Furniture types supported by the complete WUE system."""

    CHAIR = "chair"
    DINING_TABLE = "dining_table"
    BOOKSHELF = "bookshelf"
