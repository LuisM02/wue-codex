"""Validation tests for AI reconstruction part proposals."""

import pytest
from pydantic import ValidationError

from app.schemas.photo_reconstruction import ReconstructionPartProposal


def test_reconstruction_part_rejects_a_self_intersecting_profile() -> None:
    with pytest.raises(ValidationError, match="non-self-intersecting"):
        ReconstructionPartProposal.model_validate({
            "component_name": "backrest",
            "component_type": "panel",
            "geometry_kind": "extruded_profile",
            "profile_points": [
                {"u": 0, "v": 0},
                {"u": 400, "v": 500},
                {"u": 400, "v": 0},
                {"u": 0, "v": 400},
            ],
            "width": 400,
            "height": 500,
            "depth": 30,
            "source_views": ["front"],
        })
