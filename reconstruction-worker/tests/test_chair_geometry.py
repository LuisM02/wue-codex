"""Controlled evidence tests, not physical reconstruction accuracy benchmarks."""

from io import BytesIO
from dataclasses import replace
from math import cos, radians, sin

import pytest
from PIL import Image, ImageDraw

from wue_worker.geometry import reconstruct
from wue_worker.imaging import analyze_image
from wue_worker.chair_pose import LeanLine, apply_backrest_lean, fit_backrest_lean


def _chair_views(*, front_apron=True, side_apron=True, rear_apron=True,
                 apron_height=22, lean=24, rounded_seat=False):
    views = {}
    for name in ("front", "back", "left", "right", "top"):
        image = Image.new("RGB", (240, 240), "#f7f5ef")
        draw = ImageDraw.Draw(image)
        wood = "#68412b"
        if name in {"front", "back"}:
            draw.rectangle((48, 22, 192, 42), fill=wood)
            for x in (52, 78, 104, 130, 156, 182):
                draw.rectangle((x, 38, x + 8, 112), fill=wood)
            if rounded_seat:
                draw.rounded_rectangle((42, 108, 198, 126), radius=9, fill=wood)
            else:
                draw.rectangle((42, 108, 198, 126), fill=wood)
            if (front_apron if name == "front" else rear_apron):
                draw.rectangle((53, 126, 188, 126 + apron_height), fill=wood)
            draw.rectangle((53, 122, 72, 220), fill=wood)
            draw.rectangle((168, 122, 188, 220), fill=wood)
        elif name in {"left", "right"}:
            draw.rectangle((150, 22, 172, 42), fill=wood)
            draw.polygon([(150, 38), (172, 38), (172 - lean, 112),
                          (150 - lean, 112)], fill=wood)
            if rounded_seat:
                draw.rounded_rectangle((48, 108, 184, 126), radius=9, fill=wood)
            else:
                draw.rectangle((48, 108, 184, 126), fill=wood)
            if side_apron:
                draw.rectangle((55, 126, 177, 126 + apron_height), fill=wood)
            draw.rectangle((55, 122, 72, 220), fill=wood)
            draw.rectangle((160, 122, 177, 220), fill=wood)
        else:
            draw.rounded_rectangle((45, 58, 195, 182), radius=12, fill=wood)
        data = BytesIO()
        image.save(data, "PNG")
        views[name] = analyze_image(name, data.getvalue())
    return views


def _parts(**kwargs):
    result = reconstruct("chair", _chair_views(**kwargs), 450, 900, 500, [])
    return {part.component_name: part for part in result.parts}


def test_visible_aprons_are_separate_from_seat_and_legs_reach_underside():
    parts = _parts()
    assert {"front_apron", "rear_apron", "left_apron", "right_apron"} <= parts.keys()
    seat = parts["seat"]
    assert seat.height < 100
    assert parts["front_apron"].height > 70
    assert parts["front_apron"].y + parts["front_apron"].height <= seat.y + 0.001
    for name in ("front_left_leg", "front_right_leg", "rear_left_leg", "rear_right_leg"):
        assert parts[name].y + parts[name].height == pytest.approx(seat.y, abs=0.001)
    assert len([name for name in parts if name.startswith("backrest_slat_")]) == 4


def test_no_visible_apron_does_not_invent_one():
    parts = _parts(front_apron=False, rear_apron=False, side_apron=False)
    assert not any(name.endswith("_apron") for name in parts)
    assert len([part for part in parts.values() if part.component_type == "leg"]) == 4


def test_rounded_seat_edge_does_not_become_an_apron():
    parts = _parts(front_apron=False, rear_apron=False, side_apron=False,
                   rounded_seat=True)
    assert not any(name.endswith("_apron") for name in parts)


def test_apron_evidence_is_independent_between_front_back_and_side():
    parts = _parts(front_apron=False, rear_apron=True, side_apron=False)
    assert "rear_apron" in parts
    assert "front_apron" not in parts
    assert "left_apron" not in parts and "right_apron" not in parts
    side_only = _parts(front_apron=False, rear_apron=False, side_apron=True)
    assert {"left_apron", "right_apron"} <= side_only.keys()
    assert "front_apron" not in side_only and "rear_apron" not in side_only


def test_changed_apron_height_changes_apron_not_seat():
    short, tall = _parts(apron_height=14), _parts(apron_height=30)
    assert tall["front_apron"].height > short["front_apron"].height + 50
    assert tall["seat"].height == short["seat"].height
    assert tall["seat"].y == short["seat"].y


def test_leaning_post_does_not_inherit_its_swept_depth_or_back_rail_depth():
    upright, leaning = _parts(lean=0), _parts(lean=36)
    for name in ("left_backrest_post", "backrest_slat_1", "right_backrest_post"):
        assert leaning[name].depth == pytest.approx(upright[name].depth, abs=5)
        assert leaning[name].z < upright[name].z
        assert leaning[name].depth < 100


def test_depth_estimate_follows_visible_member_width():
    from dataclasses import replace

    views = _chair_views(lean=24)
    side = views["right"]
    mask = bytearray(side.mask)
    left, top, _, _ = side.bbox
    # Widen only the backrest columns, not seat/apron/leg evidence.
    for row in range(25, 70):
        offset = (top + row) * side.width + left
        active = [x for x in range(side.object_width) if mask[offset + x]]
        if active:
            for x in range(max(0, min(active) - 8), max(active) + 1):
                mask[offset + x] = 1
    views["right"] = replace(side, mask=bytes(mask))
    wider = reconstruct("chair", views, 450, 900, 500, [])
    parts = {part.component_name: part for part in wider.parts}
    baseline = _parts(lean=24)
    assert parts["backrest_slat_1"].depth > baseline["backrest_slat_1"].depth + 15


def _mirrored(view, name="left"):
    def flip(data):
        return b"".join(data[y * view.width:(y + 1) * view.width][::-1] for y in range(view.height))
    left, top, right, bottom = view.bbox
    return replace(view, name=name, mask=flip(view.mask), grayscale=flip(view.grayscale),
                   bbox=(view.width - right, top, view.width - left, bottom))


def _paired_views(lean=18):
    views = _chair_views(lean=lean)
    views["left"] = _mirrored(views["right"])
    return views


def _paired_parts(lean=18):
    response = reconstruct("chair", _paired_views(lean), 450, 900, 500, [])
    return {part.component_name: part for part in response.parts}, response.warnings


def test_consistent_opposite_views_fit_rearward_posts_and_slats_not_rail_legs_or_seat():
    parts, warnings = _paired_parts()
    upper = [part for name, part in parts.items() if "backrest_post" in name or name.startswith("backrest_slat_")]
    assert upper and all(1 < part.rotation_x < 18 for part in upper)
    assert len({part.rotation_x for part in upper}) == 1
    assert all(part.rotation_x == 0 for name, part in parts.items() if part not in upper)
    assert any("supported by both" in warning for warning in warnings)
    assert any("do not establish a measured physical angle" in warning for warning in warnings)


def test_tilt_conversion_preserves_vertical_envelope_and_center():
    baseline = _parts(lean=18)  # Wrongly oriented left view: conservative upright fallback.
    fitted, _ = _paired_parts(18)
    for name in ("left_backrest_post", "backrest_slat_1", "right_backrest_post"):
        part, old = fitted[name], baseline[name]
        angle = radians(part.rotation_x)
        assert part.height * cos(angle) + part.depth * abs(sin(angle)) == pytest.approx(old.height, abs=.002)
        assert part.y + part.height / 2 == pytest.approx(old.y + old.height / 2, abs=.002)
        assert part.depth / cos(angle) == pytest.approx(old.depth, abs=.002)
        assert all(0 <= p.u <= part.width and 0 <= p.v <= part.height for p in part.profile_points)
        half_z = (part.height * abs(sin(angle)) + part.depth * cos(angle)) / 2
        center_z = part.z + part.depth / 2
        assert 0 <= center_z - half_z <= center_z + half_z <= 500


def test_stronger_supported_lean_changes_angle_not_front_part_count():
    slight, _ = _paired_parts(12)
    strong, _ = _paired_parts(24)
    assert strong.keys() == slight.keys()
    assert strong["backrest_slat_1"].rotation_x > slight["backrest_slat_1"].rotation_x + 3


@pytest.mark.parametrize("lean", [0, 60])
def test_upright_or_excessive_angle_does_not_receive_cosmetic_rotation(lean):
    parts, warnings = _paired_parts(lean)
    assert all(part.rotation_x == 0 for part in parts.values())
    assert any("lean was not fitted" in warning for warning in warnings)


def test_disagreeing_views_keep_original_upright_proposal():
    views = _paired_views(24)
    views["left"] = _mirrored(_chair_views(lean=0)["right"])
    result = reconstruct("chair", views, 450, 900, 500, [])
    assert all(part.rotation_x == 0 for part in result.parts)


def test_missing_or_widely_split_side_evidence_does_not_fit_a_line():
    views = _paired_views()
    side = views["left"]
    views["left"] = replace(side, mask=bytes(len(side.mask)))
    assert fit_backrest_lean(views, .12, .44, 900, 500) is None
    mask = bytearray(side.mask)
    left, top, _, _ = side.bbox
    for row in range(20, 95):
        mask[(top + row) * side.width + left + round(side.object_width * .8)] = 1
    views["left"] = replace(side, mask=bytes(mask))
    assert fit_backrest_lean(views, .12, .44, 900, 500) is None


def test_out_of_bounds_assembly_rejects_whole_pose_without_mutating_input():
    parts = list(_parts(lean=18).values())
    before = [part.model_dump() for part in parts]
    assert apply_backrest_lean(parts, LeanLine(.2, 490), 900, 500) is None
    assert [part.model_dump() for part in parts] == before


def test_flat_unresolved_outline_has_no_post_assembly_to_tilt():
    parts = [part for part in _parts().values() if "backrest_post" not in part.component_name and not part.component_name.startswith("backrest_slat_")]
    assert apply_backrest_lean(parts, LeanLine(.1, 300), 900, 500) is None


def test_missing_slot_or_invalid_sampling_window_is_not_pose_evidence():
    views = _paired_views()
    assert fit_backrest_lean({"right": views["right"]}, .1, .4, 900, 500) is None
    for low, high in ((-.1, .4), (.4, .1), (.1, 1.1)):
        assert fit_backrest_lean(views, low, high, 900, 500) is None
