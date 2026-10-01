"""Controlled shelf-edge evidence, not a physical accuracy benchmark."""

from io import BytesIO
import hashlib
import json

import pytest
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient

from wue_worker.geometry import _bookshelf, _bookshelf_edge_bands, _coherent_photo_edges
from wue_worker.imaging import analyze_image
from wue_worker.main import app
from wue_worker.segmentation import BaselineSegmentationProvider, get_segmentation_provider


def _backed_photo(positions=(65, 108, 151, 194), *, thickness=5,
                  short=False, grain=False, dark=False, marker=0):
    image = Image.new("RGB", (240, 280), "#fafafa")
    draw = ImageDraw.Draw(image)
    draw.rectangle((35, 15, 205, 260), fill="#c4a278")
    draw.rectangle((44, 24, 196, 245), fill="#745337" if not dark else "#ad8b66")
    if grain:
        for x in range(48, 193, 8):
            draw.line((x, 28, x, 241), fill="#392b20", width=2)
    for y in positions:
        draw.rectangle((44 if not short else 95, y, 196 if not short else 145, y + thickness - 1),
                       fill="#deb887" if not dark else "#3c291c")
    data = BytesIO()
    draw.point((5 + marker, 5), fill="#cccccc")
    image.save(data, "PNG")
    return data.getvalue()


def _backed_view(*args, **kwargs):
    return analyze_image("front", _backed_photo(*args, **kwargs))


def _parts(view):
    parts, warnings = _bookshelf({"front": view}, 600, 1200, 300)
    return {part.component_name: part for part in parts}, warnings


def test_solid_back_preserves_four_visible_shelves_and_full_width_bottom():
    view = _backed_view()
    assert view.fill_ratio > .9
    parts, warnings = _parts(view)
    assert [name for name in parts if name.startswith("shelf_")] == [
        "shelf_1", "shelf_2", "shelf_3", "shelf_4",
    ]
    assert parts["bottom_panel"].width == parts["shelf_1"].width
    assert parts["bottom_panel"].width > 500
    assert parts["left_side"].height == parts["right_side"].height
    assert all(part.source_views == ["front"] for part in parts.values())
    assert any("provisional" in warning for warning in warnings)


@pytest.mark.parametrize("dark", [False, True])
def test_contrast_polarity_and_changed_count_follow_photo(dark):
    parts, _ = _parts(_backed_view((74, 174), dark=dark))
    assert len([name for name in parts if name.startswith("shelf_")]) == 2


def test_moving_one_shelf_changes_its_position_not_other_shelves():
    first, _ = _parts(_backed_view((65, 108, 151, 194)))
    moved, _ = _parts(_backed_view((65, 118, 151, 194)))
    assert moved["shelf_2"].y < first["shelf_2"].y - 30
    assert moved["shelf_1"].y == first["shelf_1"].y
    assert moved["shelf_3"].y == first["shelf_3"].y


def test_thicker_observed_face_changes_shelf_height():
    thin, _ = _parts(_backed_view(thickness=3))
    thick, _ = _parts(_backed_view(thickness=7))
    assert thick["shelf_1"].height > thin["shelf_1"].height


@pytest.mark.parametrize("kwargs", [
    {"positions": ()}, {"positions": (), "grain": True},
    {"short": True}, {"thickness": 1},
])
def test_box_grain_short_objects_and_single_pixel_lines_do_not_invent_shelves(kwargs):
    with pytest.raises(ValueError, match="No reliable internal shelf boundaries"):
        _parts(_backed_view(**kwargs))


def test_shadow_pair_does_not_duplicate_a_shelf_face():
    view = _backed_view()
    bands = _bookshelf_edge_bands(view, [(50, -18), (56, 35), (62, -80)])
    assert bands == [(56, 62)]
    assert len(_bookshelf_edge_bands(view, _coherent_photo_edges(view))) == 4


@pytest.mark.parametrize("positions,expected_status", [((65, 108, 151, 194), 200), ((), 422)])
def test_worker_http_reports_detected_shelves_or_explicit_failure(positions, expected_status):
    views = ("front", "back", "left", "right", "top")
    photos = {view: _backed_photo(positions, marker=index) for index, view in enumerate(views)}
    app.dependency_overrides[get_segmentation_provider] = BaselineSegmentationProvider
    try:
        with TestClient(app) as client:
            response = client.post("/v1/reconstruct", files={
                view: (f"{view}.png", data, "image/png") for view, data in photos.items()
            }, data={
                "furniture_type": "bookshelf", "width_mm": "600", "height_mm": "1200",
                "depth_mm": "600", "image_manifest": json.dumps([
                    {"view": view, "checksum_sha256": hashlib.sha256(data).hexdigest()}
                    for view, data in photos.items()
                ]),
            })
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == expected_status, response.text
    if expected_status == 200:
        assert len(response.json()["parts"]) == 9
    else:
        assert "will not insert a guessed middle shelf" in response.json()["detail"]
