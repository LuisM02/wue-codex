"""Parametric plan component schema tests."""

import pytest
from pydantic import ValidationError

from app.schemas.plans import ComponentCreate, ComponentUpdate


def valid_component() -> dict[str, object]:
    return {
        "component_name": " custom_panel ",
        "component_type": "panel",
        "width": "500.0000",
        "height": "20.0000",
        "thickness": "20.0000",
    }


def test_component_input_normalizes_name_and_defaults_transform() -> None:
    component = ComponentCreate.model_validate(valid_component())

    assert component.component_name == "custom_panel"
    assert component.x == component.y == component.z == 0
    assert component.rotation == 0
    assert component.rotation_x == component.rotation_y == component.rotation_z == 0
    assert component.geometry_kind.value == "box"
    assert component.profile_points is None
    assert component.quantity == 1
    assert component.sort_order == 0
    assert component.depth is None


def test_draft_component_can_defer_both_depth_fields_until_3d_validation() -> None:
    payload = valid_component()
    payload.pop("thickness")

    component = ComponentCreate.model_validate(payload)

    assert component.depth is None
    assert component.thickness is None


@pytest.mark.parametrize(
    "override",
    [
        {"component_type": "support"},
        {"width": 0},
        {"height": -1},
        {"thickness": 0},
        {"quantity": 0},
        {"sort_order": -1},
        {"unexpected": True},
    ],
)
def test_component_input_rejects_unsupported_or_invalid_values(
    override: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        ComponentCreate.model_validate({**valid_component(), **override})


@pytest.mark.parametrize("payload", [{}, {"width": None}, {"component_name": None}])
def test_component_update_requires_a_non_null_mutation(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        ComponentUpdate.model_validate(payload)


def test_component_update_can_clear_optional_depth_fields() -> None:
    update = ComponentUpdate.model_validate({"depth": None, "thickness": None})

    assert update.model_dump(exclude_unset=True) == {
        "depth": None,
        "thickness": None,
    }


def test_extruded_profile_requires_a_real_outline_inside_part_bounds() -> None:
    component = ComponentCreate.model_validate({
        **valid_component(),
        "geometry_kind": "extruded_profile",
        "profile_points": [
            {"u": 0, "v": 0},
            {"u": 500, "v": 0},
            {"u": 400, "v": 20},
            {"u": 20, "v": 20},
        ],
    })

    assert len(component.profile_points or []) == 4

    with pytest.raises(ValidationError):
        ComponentCreate.model_validate({
            **valid_component(),
            "geometry_kind": "extruded_profile",
            "profile_points": [{"u": 0, "v": 0}, {"u": 600, "v": 0}, {"u": 0, "v": 20}],
        })


def test_extruded_profile_rejects_a_self_intersecting_outline() -> None:
    with pytest.raises(ValidationError, match="non-self-intersecting"):
        ComponentCreate.model_validate({
            **valid_component(),
            "geometry_kind": "extruded_profile",
            "profile_points": [
                {"u": 0, "v": 0},
                {"u": 500, "v": 20},
                {"u": 500, "v": 0},
                {"u": 0, "v": 15},
            ],
        })
