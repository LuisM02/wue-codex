"""Regression checks for rails joining leg silhouettes and stray mask islands."""

from wue_worker.geometry import _chair_leg_regions, trace_region
from wue_worker.imaging import AnalyzedView


def view_from_rectangles(rectangles):
    width, height = 120, 200
    mask = bytearray(width * height)
    for left, top, right, bottom in rectangles:
        for y in range(top, bottom):
            for x in range(left, right):
                mask[y * width + x] = 1
    return AnalyzedView(
        name="front", width=width, height=height, mask=bytes(mask),
        bbox=(0, 0, width, height), object_pixels=sum(mask),
        foreground_pixels=sum(mask), checksum_sha256="0" * 64,
        grayscale=bytes(width * height),
    )


def test_horizontal_stretcher_does_not_merge_two_legs():
    view = view_from_rectangles([
        (10, 100, 24, 200), (90, 100, 104, 200),
        (10, 150, 104, 160),
    ])
    assert _chair_leg_regions(view, 100) == [(10, 24), (90, 104)]


def test_primary_profile_ignores_disconnected_backrest_islands():
    view = view_from_rectangles([(20, 5, 80, 40), (95, 10, 101, 30)])
    region = trace_region(
        view, 0, 0, 120, 45, 600, 1000, primary_span_only=True,
    )
    assert region.x == 100
    assert region.width == 300
    assert region.height == 175
