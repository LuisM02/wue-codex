"""Controlled evidence tests, not physical reconstruction accuracy benchmarks."""

from io import BytesIO

import pytest
from PIL import Image, ImageDraw

from wue_worker.geometry import reconstruct
from wue_worker.imaging import analyze_image


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
