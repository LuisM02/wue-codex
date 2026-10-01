"""Turn analyzed five-view silhouettes into editable, measured part proposals."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from .imaging import AnalyzedView
from .chair_pose import apply_backrest_lean, fit_backrest_lean
from .schemas import PartProposal, ProfilePoint, ReconstructionResponse


def _rounded(value: float) -> float:
    return round(max(value, 0.0001), 4)


def _smooth(values: list[float], radius: int = 2) -> list[float]:
    return [
        sum(values[max(0, index - radius) : min(len(values), index + radius + 1)])
        / max(1, min(len(values), index + radius + 1) - max(0, index - radius))
        for index in range(len(values))
    ]


def _strongest_band(
    view: AnalyzedView, low: float, high: float
) -> tuple[int, int, int]:
    rows = _smooth(view.rows())
    height = len(rows)
    start = max(0, int(height * low))
    stop = min(height, max(start + 1, int(height * high)))
    center = max(range(start, stop), key=lambda index: rows[index])
    peak = rows[center]
    upper = center
    lower = center + 1
    limit = max(2, int(height * 0.12))
    while upper > 0 and center - upper < limit and rows[upper - 1] >= peak * 0.72:
        upper -= 1
    while lower < height and lower - center < limit and rows[lower] >= peak * 0.72:
        lower += 1
    if lower - upper > limit:
        half = max(1, limit // 2)
        upper, lower = max(0, center - half), min(height, center + half + 1)
    return upper, lower, center


def _spans(
    values: list[float], threshold: float, *, gap: int = 2, minimum: int = 2
) -> list[tuple[int, int]]:
    active = [index for index, value in enumerate(values) if value >= threshold]
    if not active:
        return []
    spans: list[tuple[int, int]] = []
    start = previous = active[0]
    for index in active[1:]:
        if index - previous > gap + 1:
            if previous + 1 - start >= minimum:
                spans.append((start, previous + 1))
            start = index
        previous = index
    if previous + 1 - start >= minimum:
        spans.append((start, previous + 1))
    return spans


@dataclass(frozen=True, slots=True)
class TracedRegion:
    width: float
    height: float
    x: float
    y: float
    points: list[ProfilePoint]


def _deduplicate(points: list[ProfilePoint]) -> list[ProfilePoint]:
    result: list[ProfilePoint] = []
    for point in points:
        if not result or (point.u, point.v) != (result[-1].u, result[-1].v):
            result.append(point)
    if len(result) > 1 and (result[0].u, result[0].v) == (
        result[-1].u,
        result[-1].v,
    ):
        result.pop()
    return result


def trace_region(
    view: AnalyzedView,
    x_start: int,
    y_start: int,
    x_stop: int,
    y_stop: int,
    overall_width: float,
    overall_height: float,
    *,
    primary_span_only: bool = False,
) -> TracedRegion:
    left, top, _, _ = view.bbox
    object_width, object_height = view.object_width, view.object_height
    occupied: list[tuple[int, int, int]] = []
    for local_y in range(max(0, y_start), min(object_height, y_stop)):
        absolute_y = top + local_y
        xs = [
            local_x
            for local_x in range(max(0, x_start), min(object_width, x_stop))
            if view.mask[absolute_y * view.width + left + local_x]
        ]
        if primary_span_only and xs:
            spans = _spans(
                [
                    1.0
                    if view.mask[absolute_y * view.width + left + local_x]
                    else 0.0
                    for local_x in range(
                        max(0, x_start), min(object_width, x_stop)
                    )
                ],
                0.5,
                gap=1,
                minimum=1,
            )
            if spans:
                row_offset = max(0, x_start)
                primary = max(spans, key=lambda span: span[1] - span[0])
                xs = list(
                    range(
                        row_offset + primary[0],
                        row_offset + primary[1],
                    )
                )
        if xs:
            occupied.append((local_y, min(xs), max(xs) + 1))
    if not occupied:
        raise ValueError("A requested part region contains no photographed silhouette")
    min_y, max_y = occupied[0][0], occupied[-1][0] + 1
    min_x = min(item[1] for item in occupied)
    max_x = max(item[2] for item in occupied)
    width_mm = (max_x - min_x) / object_width * overall_width
    height_mm = (max_y - min_y) / object_height * overall_height
    x_mm = min_x / object_width * overall_width
    y_mm = (object_height - max_y) / object_height * overall_height
    stride = max(1, len(occupied) // 20)
    sampled = occupied[::stride]
    if sampled[-1] != occupied[-1]:
        sampled.append(occupied[-1])

    def point(pixel_x: int, pixel_y: int) -> ProfilePoint:
        u = (pixel_x - min_x) / max(1, max_x - min_x) * width_mm
        v = (max_y - pixel_y) / max(1, max_y - min_y) * height_mm
        return ProfilePoint(u=_rounded(u), v=_rounded(v))

    left_edge = [
        point(row_left, row_y + 1)
        for row_y, row_left, _ in reversed(sampled)
    ]
    right_edge = [
        point(row_right, row_y) for row_y, _, row_right in sampled
    ]
    points = _deduplicate(left_edge + right_edge)
    if len(points) < 3:
        points = [
            ProfilePoint(u=0, v=0),
            ProfilePoint(u=_rounded(width_mm), v=0),
            ProfilePoint(u=_rounded(width_mm), v=_rounded(height_mm)),
            ProfilePoint(u=0, v=_rounded(height_mm)),
        ]
    return TracedRegion(
        width=_rounded(width_mm),
        height=_rounded(height_mm),
        x=_rounded(x_mm),
        y=_rounded(y_mm),
        points=points,
    )


def _span_at_rows(
    view: AnalyzedView, y_start: int, y_stop: int
) -> tuple[int, int]:
    values = view.columns(y_start, y_stop)
    spans = _spans(
        values, 0.12, gap=max(1, len(values) // 50), minimum=2
    )
    if not spans:
        return 0, view.object_width
    return min(span[0] for span in spans), max(span[1] for span in spans)


def _depth_geometry(
    side: AnalyzedView,
    y_start: int,
    y_stop: int,
    overall_depth: float,
) -> tuple[float, float]:
    start, stop = _span_at_rows(side, y_start, y_stop)
    return (
        _rounded((stop - start) / side.object_width * overall_depth),
        _rounded(start / side.object_width * overall_depth),
    )


def _proposal(
    name: str,
    component_type: str,
    region: TracedRegion,
    depth: float,
    z: float,
    order: int,
    confidence: float,
    source_views: list[str],
) -> PartProposal:
    return PartProposal(
        component_name=name,
        component_type=component_type,
        geometry_kind="extruded_profile",
        profile_points=region.points,
        width=region.width,
        height=region.height,
        depth=_rounded(depth),
        x=region.x,
        y=region.y,
        z=_rounded(z),
        sort_order=order,
        confidence=round(confidence, 3),
        source_views=source_views,
    )


def _leg_regions(view: AnalyzedView, start_y: int) -> list[tuple[int, int]]:
    height = view.object_height - start_y
    threshold = max(0.10, min(0.35, 5 / max(1, height)))
    spans = _spans(
        view.columns(start_y, view.object_height),
        threshold,
        gap=max(1, view.object_width // 80),
        minimum=max(2, view.object_width // 80),
    )
    if not spans:
        return [(0, view.object_width)]
    if len(spans) > 2:
        spans = sorted(
            spans, key=lambda item: item[1] - item[0], reverse=True
        )[:2]
        spans.sort()
    return spans


def _dominant_band(
    view: AnalyzedView,
    start_y: int,
    stop_y: int,
    *,
    minimum_density: float,
) -> tuple[int, int, int]:
    """Return the strongest sustained photographed band inside a row range."""
    rows = _smooth(view.rows(), radius=1)
    start = max(0, min(len(rows) - 1, start_y))
    stop = max(start + 1, min(len(rows), stop_y))
    window = rows[start:stop]
    peak = max(window)
    threshold = max(minimum_density, peak * 0.68)
    spans = _spans(
        window,
        threshold,
        gap=2,
        minimum=max(2, view.object_height // 100),
    )
    if not spans:
        return _strongest_band(
            view,
            start / view.object_height,
            stop / view.object_height,
        )
    local_start, local_stop = max(
        spans,
        key=lambda span: sum(window[span[0] : span[1]]),
    )
    band_start = start + local_start
    band_stop = start + local_stop
    center = max(
        range(band_start, band_stop),
        key=lambda index: rows[index],
    )
    return band_start, band_stop, center


def _chair_leg_regions(
    view: AnalyzedView, seat_bottom: int
) -> list[tuple[int, int]]:
    """Find legs below horizontal rails, where their columns are separable."""
    start = max(seat_bottom + 2, round(view.object_height * 0.72))
    stop = min(view.object_height, max(start + 2, round(view.object_height * 0.96)))
    values = view.columns(start, stop)
    spans = _spans(
        values,
        0.48,
        gap=max(1, view.object_width // 100),
        minimum=max(2, view.object_width // 100),
    )
    if len(spans) < 2:
        spans = _spans(
            values,
            0.30,
            gap=max(1, view.object_width // 100),
            minimum=max(2, view.object_width // 100),
        )
    if len(spans) < 2:
        return _leg_regions(view, start)
    if len(spans) > 2:
        spans = sorted(
            spans,
            key=lambda item: sum(values[item[0] : item[1]]),
            reverse=True,
        )[:2]
    return sorted(spans)


def _rectangle_region(
    width: float,
    height: float,
    x: float,
    y: float,
) -> TracedRegion:
    measured_width = _rounded(width)
    measured_height = _rounded(height)
    return TracedRegion(
        width=measured_width,
        height=measured_height,
        x=_rounded(x),
        y=_rounded(y),
        points=[
            ProfilePoint(u=0, v=0),
            ProfilePoint(u=measured_width, v=0),
            ProfilePoint(u=measured_width, v=measured_height),
            ProfilePoint(u=0, v=measured_height),
        ],
    )


def _chair_rail_region(
    view: AnalyzedView,
    seat_bottom: int,
    leg_spans: list[tuple[int, int]],
    overall_width: float,
    overall_height: float,
) -> TracedRegion | None:
    """Trace a wide horizontal stretcher while ignoring the two leg columns."""
    if len(leg_spans) != 2:
        return None
    interior_start = leg_spans[0][1]
    interior_stop = leg_spans[1][0]
    if interior_stop - interior_start < max(4, view.object_width // 8):
        return None
    start_y = max(
        seat_bottom + max(2, round(view.object_height * 0.05)),
        round(view.object_height * 0.59),
    )
    stop_y = min(view.object_height, round(view.object_height * 0.86))
    if stop_y - start_y < 2:
        return None

    row_spans: list[tuple[int, tuple[int, int], int]] = []
    left, top, _, _ = view.bbox
    for y in range(start_y, stop_y):
        values = [
            view.mask[(top + y) * view.width + left + x]
            for x in range(interior_start, interior_stop)
        ]
        spans = _spans(values, 0.5, gap=1, minimum=2)
        if spans:
            longest = max(spans, key=lambda span: span[1] - span[0])
            row_spans.append(
                (
                    y,
                    (interior_start + longest[0], interior_start + longest[1]),
                    longest[1] - longest[0],
                )
            )
    if not row_spans:
        return None
    peak = max(item[2] for item in row_spans)
    if peak < max(4, round(view.object_width * 0.20)):
        return None
    qualifying = [
        item for item in row_spans if item[2] >= max(3, round(peak * 0.65))
    ]
    bands = _spans(
        [
            1.0 if any(item[0] == y for item in qualifying) else 0.0
            for y in range(start_y, stop_y)
        ],
        0.5,
        gap=2,
        minimum=2,
    )
    if not bands:
        return None
    band = max(
        bands,
        key=lambda span: sum(
            item[2]
            for item in qualifying
            if start_y + span[0] <= item[0] < start_y + span[1]
        ),
    )
    band_start, band_stop = start_y + band[0], start_y + band[1]
    selected = [item for item in qualifying if band_start <= item[0] < band_stop]
    x_start = min(item[1][0] for item in selected)
    x_stop = max(item[1][1] for item in selected)
    return trace_region(
        view,
        x_start,
        band_start,
        x_stop,
        band_stop,
        overall_width,
        overall_height,
    )


def _chair_apron_band(
    view: AnalyzedView, seat_center: int, band_bottom: int
) -> tuple[int, int] | None:
    """Find a sustained narrower band after the seat's widest lip.

    Follow the observed dense seat band beyond a truncated search window.
    Sloped/rounded seat edges are not enough evidence, and a leg-only row
    must end the search before a separate lower stretcher is reached.
    """
    rows = view.rows()
    peak = max(rows[max(0, seat_center - 3):seat_center + 4], default=0)
    tolerance = 1.5 / view.object_width
    minimum_rows = max(4, round(view.object_height * 0.025))
    start = None
    stop = seat_center
    density_at_start = 0.0
    search_stop = min(len(rows), max(band_bottom + 1, round(len(rows) * 0.72)))
    for row in range(seat_center, search_stop):
        density = rows[row]
        if density < max(0.52, peak * 0.65):
            break
        if density >= peak - tolerance:
            start = None
            continue
        if start is None or abs(density - density_at_start) > tolerance:
            if start is not None and stop - start >= minimum_rows:
                return start, stop
            start, density_at_start = row, density
        stop = row + 1
    if start is None or stop - start < minimum_rows:
        return None
    return start, stop


def _row_depth_estimate(
    side: AnalyzedView, start_y: int, stop_y: int, overall_depth: float
) -> tuple[float, float]:
    """Estimate local cross-section from row spans, not the swept envelope.

    A leaning post must not inherit the width of its entire travel through Z.
    The median location is still a straight extrusion approximation; neither
    camera pose nor hidden member thickness can be established by this method.
    """
    left, top, _, _ = side.bbox
    samples = []
    for row in range(max(0, start_y), min(side.object_height, stop_y)):
        offset = (top + row) * side.width + left
        spans = _spans(
            list(side.mask[offset:offset + side.object_width]),
            0.5, gap=0, minimum=2,
        )
        if spans:
            samples.append(max(spans, key=lambda span: span[1] - span[0]))
    if len(samples) < 3:
        return _depth_geometry(side, start_y, stop_y, overall_depth)
    thickness = median(stop - start for start, stop in samples)
    center = median((start + stop) / 2 for start, stop in samples)
    return (
        _rounded(thickness / side.object_width * overall_depth),
        _rounded((center - thickness / 2) / side.object_width * overall_depth),
    )


def _chair(
    views: dict[str, AnalyzedView], width: float, height: float, depth: float
) -> tuple[list[PartProposal], list[str]]:
    # In a conventional right elevation the chair's front is on the left,
    # matching increasing canonical Z from front to back. A left elevation
    # would reverse rear/backrest placement unless explicitly mirrored.
    front, side = views["front"], views["right"]
    seat_top, seat_bottom, seat_center = _dominant_band(
        front,
        round(front.object_height * 0.28),
        round(front.object_height * 0.64),
        minimum_density=0.52,
    )
    front_apron_band = _chair_apron_band(front, seat_center, seat_bottom)
    seat_underside = front_apron_band[0] if front_apron_band else seat_bottom
    side_seat_top, side_band_bottom, side_center = _dominant_band(
        side, round(side.object_height * 0.28),
        round(side.object_height * 0.64), minimum_density=0.52,
    )
    side_apron_band = _chair_apron_band(side, side_center, side_band_bottom)
    side_underside = side_apron_band[0] if side_apron_band else side_band_bottom
    seat = trace_region(
        front,
        0,
        seat_top,
        front.object_width,
        seat_underside,
        width,
        height,
        primary_span_only=True,
    )
    seat_depth, seat_z = _depth_geometry(
        side,
        side_seat_top,
        side_underside,
        depth,
    )
    parts = [
        _proposal(
            "seat",
            "panel",
            seat,
            seat_depth,
            seat_z,
            0,
            0.66,
            ["front", "back", "left", "right", "top"],
        )
    ]
    if seat_top <= max(3, front.object_height // 12):
        raise ValueError("The chair backrest could not be separated from the seat")
    back_top, back_bottom, _ = _dominant_band(
        front,
        0,
        seat_top,
        minimum_density=0.48,
    )
    backrest = trace_region(
        front,
        0,
        back_top,
        front.object_width,
        back_bottom,
        width,
        height,
        primary_span_only=True,
    )
    back_depth, back_z = _row_depth_estimate(
        side,
        round(back_top / front.object_height * side.object_height),
        max(
            2,
            round(back_bottom / front.object_height * side.object_height),
        ),
        depth,
    )
    parts.append(
        _proposal(
            "backrest",
            "panel",
            backrest,
            back_depth,
            back_z,
            1,
            0.61,
            ["front", "back", "left", "right"],
        )
    )

    order = 2
    post_depth, post_z = _row_depth_estimate(
        side,
        round(back_bottom / front.object_height * side.object_height),
        round(seat_top / front.object_height * side.object_height),
        depth,
    )
    post_spans = _spans(
        front.columns(back_bottom, seat_top),
        0.42,
        gap=max(1, front.object_width // 100),
        minimum=max(2, front.object_width // 100),
    )
    if len(post_spans) >= 2:
        for index, span in enumerate(post_spans):
            name = (
                "left_backrest_post" if index == 0
                else "right_backrest_post" if index == len(post_spans) - 1
                else f"backrest_slat_{index}"
            )
            post = trace_region(
                front,
                span[0],
                back_bottom,
                span[1],
                seat_top,
                width,
                height,
            )
            parts.append(
                _proposal(
                    name,
                    "panel",
                    post,
                    post_depth,
                    post_z,
                    order,
                    0.55,
                    ["front", "back", "left", "right"],
                )
            )
            order += 1

    front_spans = _chair_leg_regions(front, seat_underside)
    side_start = min(side.object_height - 1, side_underside)
    depth_spans = _chair_leg_regions(side, side_start)
    front_labels = ["left", "right"] if len(front_spans) == 2 else ["center"]
    depth_labels = ["front", "rear"] if len(depth_spans) == 2 else ["center"]
    for depth_index, depth_span in enumerate(depth_spans):
        for front_index, front_span in enumerate(front_spans):
            region = trace_region(
                front,
                front_span[0],
                seat_underside,
                front_span[1],
                front.object_height,
                width,
                height,
            )
            part_depth = (
                (depth_span[1] - depth_span[0]) / side.object_width * depth
            )
            z = depth_span[0] / side.object_width * depth
            if len(front_spans) == 2 and len(depth_spans) == 2:
                name = (
                    f"{depth_labels[depth_index]}_"
                    f"{front_labels[front_index]}_leg"
                )
            else:
                name = (
                    f"{depth_labels[depth_index]}_"
                    f"{front_labels[front_index]}_support"
                )
            parts.append(
                _proposal(
                    name,
                    "leg",
                    region,
                    part_depth,
                    z,
                    order,
                    0.54,
                    ["front", "back", "left", "right"],
                )
            )
            order += 1

    # Each photographed elevation must provide its own apron evidence. A
    # right-side band supports a provisional symmetric pair, not a hidden
    # joinery claim. Aprons stop between legs rather than filling the seat.
    if len(depth_spans) == 2:
        for label, elevation, span in (
            ("front", front, depth_spans[0]),
            ("rear", views["back"], depth_spans[1]),
        ):
            if label == "front":
                band, leg_spans = front_apron_band, front_spans
            else:
                _, bottom, center = _dominant_band(
                    elevation, round(elevation.object_height * 0.28),
                    round(elevation.object_height * 0.64), minimum_density=0.52,
                )
                band = _chair_apron_band(elevation, center, bottom)
                leg_spans = _chair_leg_regions(elevation, bottom)
            if band is None or len(leg_spans) != 2 or leg_spans[1][0] <= leg_spans[0][1]:
                continue
            apron = trace_region(
                elevation, leg_spans[0][1], band[0], leg_spans[1][0],
                band[1], width, height,
            )
            if label == "rear":
                apron = TracedRegion(
                    width=apron.width, height=apron.height,
                    x=_rounded(width - apron.x - apron.width), y=apron.y,
                    points=[
                        ProfilePoint(u=_rounded(apron.width - point.u), v=point.v)
                        for point in reversed(apron.points)
                    ],
                )
            parts.append(_proposal(
                f"{label}_apron", "panel", apron,
                (span[1] - span[0]) / side.object_width * depth,
                span[0] / side.object_width * depth, order, 0.48,
                [label if label == "front" else "back", "right"],
            ))
            order += 1
    if side_apron_band is not None and len(front_spans) == len(depth_spans) == 2:
        inner_start, inner_stop = depth_spans[0][1], depth_spans[1][0]
        if inner_stop > inner_start:
            side_apron = trace_region(
                side, inner_start, side_apron_band[0], inner_stop,
                side_apron_band[1], depth, height,
            )
            for label, span in zip(("left", "right"), front_spans, strict=True):
                apron = _rectangle_region(
                    (span[1] - span[0]) / front.object_width * width,
                    side_apron.height, span[0] / front.object_width * width,
                    side_apron.y,
                )
                parts.append(_proposal(
                    f"{label}_apron", "panel", apron, side_apron.width,
                    side_apron.x, order, 0.46, ["right", "front"],
                ))
                order += 1

    front_rail = _chair_rail_region(
        front,
        seat_bottom,
        front_spans,
        width,
        height,
    )
    if front_rail is not None and depth_spans:
        front_depth_span = depth_spans[0]
        parts.append(
            _proposal(
                "front_stretcher",
                "panel",
                front_rail,
                (front_depth_span[1] - front_depth_span[0])
                / side.object_width
                * depth,
                front_depth_span[0] / side.object_width * depth,
                order,
                0.5,
                ["front", "back"],
            )
        )
        order += 1

    side_rail = _chair_rail_region(
        side,
        side_start,
        depth_spans,
        depth,
        height,
    )
    if side_rail is not None and len(front_spans) == 2:
        for label, span in zip(("left", "right"), front_spans, strict=True):
            x = span[0] / front.object_width * width
            rail_width = (span[1] - span[0]) / front.object_width * width
            rail = _rectangle_region(
                rail_width,
                side_rail.height,
                x,
                side_rail.y,
            )
            parts.append(
                _proposal(
                    f"{label}_stretcher",
                    "panel",
                    rail,
                    side_rail.width,
                    side_rail.x,
                    order,
                    0.5,
                    ["left", "right"],
                )
            )
            order += 1
    warnings = [
        "Hidden joinery and occluded rear surfaces are inferred; verify them in the part editor",
        "Chair front/back placement uses the right-side photograph; mirror the left reference overlay when comparing the Side view",
        "Backrest/slat depths use side-view row envelopes, not verified timber thicknesses; curved and overlapping members remain straight-extrusion approximations",
        "Seat thickness remains a perspective-projected band; visible apron bands are separated but flush or hidden aprons may require manual correction",
        "Paired side aprons and occluded member thicknesses assume symmetry; verify against both side photographs",
        "Seat, backrest, posts, legs, and visible stretchers are separated from the photographed silhouette; confirm overlapping rails before manufacture",
        "Front/back and left/right labels assume the photographs were placed in the requested slots",
    ]
    lean = fit_backrest_lean(
        views, back_bottom / front.object_height, seat_top / front.object_height,
        height, depth,
    )
    tilted = apply_backrest_lean(parts, lean, height, depth) if lean is not None else None
    if tilted is not None:
        parts = tilted
        warnings.append(
            "Backrest posts/slats use a straight projected lean supported by both mirrored-left and right silhouettes; "
            "the supplied scale and unrectified photos do not establish a measured physical angle. "
            "Top rail and rear legs are not automatically tilted; verify their connections."
        )
    else:
        warnings.append(
            "Backrest lean was not fitted: both side silhouettes must agree on a stable centerline within the supplied bounds; "
            "verify tilt manually rather than treating upright proposals as measured."
        )
    return parts, warnings


def _table_apron_band(view: AnalyzedView, start: int) -> tuple[int, int] | None:
    """Require a stable narrower band beneath the slab, not its curved edge.

    The slab search is deliberately capped because perspective exaggerates
    its thickness. Its unconsumed rows must not become invented apron panels.
    A small overhang is sufficient; require several stable rows so rounded
    slab corners alone do not create an apron. Fully flush/hidden bands remain
    uncertain rather than being fabricated.
    """
    rows = view.rows()
    search_stop = round(view.object_height * 0.4)
    peak = max(rows[:search_stop], default=1.0)
    pixel_tolerance = 1.5 / view.object_width
    minimum_rows = max(4, round(view.object_height * 0.03))
    band_start = None
    band_stop = start
    band_density = 0.0
    for row, density in enumerate(rows[start:search_stop], start):
        if density < 0.55:
            break
        if density > peak - pixel_tolerance:
            band_start = None
            continue
        if band_start is None or abs(density - band_density) > pixel_tolerance:
            if band_start is not None and band_stop - band_start >= minimum_rows:
                return band_start, band_stop
            band_start = row
            band_density = density
        band_stop = row + 1
    if band_start is None or band_stop - band_start < minimum_rows:
        return None
    return band_start, band_stop


def _dining_table(
    views: dict[str, AnalyzedView], width: float, height: float, depth: float
) -> tuple[list[PartProposal], list[str]]:
    front, side = views["front"], views["left"]
    top_start, top_stop, _ = _strongest_band(front, 0.02, 0.42)
    tabletop_projection = trace_region(
        front, 0, 0, front.object_width, top_stop, width, height
    )
    # The photographed top surface is foreshortened into the front elevation.
    # Its projected height is not a trustworthy physical slab thickness.
    top_thickness = min(tabletop_projection.height, height * 0.065)
    underside_height = height - top_thickness
    vertical_scale = (
        front.object_height / max(1, front.object_height - top_stop)
        * underside_height / height
    )

    def remap_vertical(
        region: TracedRegion, scale: float, *, y: float | None = None
    ) -> TracedRegion:
        return TracedRegion(
            width=region.width,
            height=_rounded(region.height * scale),
            x=region.x,
            y=_rounded(region.y * scale if y is None else y),
            points=[
                ProfilePoint(u=point.u, v=_rounded(point.v * scale))
                for point in region.points
            ],
        )

    tabletop = remap_vertical(
        tabletop_projection,
        top_thickness / tabletop_projection.height,
        y=underside_height,
    )
    side_top_start = round(
        top_start / front.object_height * side.object_height
    )
    side_top_stop = max(
        side_top_start + 1,
        round(top_stop / front.object_height * side.object_height),
    )
    top_depth, top_z = _depth_geometry(
        side, side_top_start, side_top_stop, depth
    )
    parts = [
        _proposal(
            "tabletop",
            "panel",
            tabletop,
            top_depth,
            top_z,
            0,
            0.68,
            ["front", "back", "left", "right", "top"],
        )
    ]
    # Sample below the apron: averaging the entire underside joins otherwise
    # distinct legs into one wide support on photographed dining tables.
    front_spans = _chair_leg_regions(front, top_stop)
    side_start = min(
        side.object_height - 1,
        round(top_stop / front.object_height * side.object_height),
    )
    depth_spans = _chair_leg_regions(side, side_start)
    order = 1
    x_labels = ["left", "right"] if len(front_spans) == 2 else ["center"]
    z_labels = ["front", "rear"] if len(depth_spans) == 2 else ["center"]
    for z_index, z_span in enumerate(depth_spans):
        for x_index, x_span in enumerate(front_spans):
            region = remap_vertical(
                trace_region(
                    front,
                    x_span[0],
                    top_stop,
                    x_span[1],
                    front.object_height,
                    width,
                    height,
                ),
                vertical_scale,
            )
            if len(front_spans) == 2 and len(depth_spans) == 2:
                name = f"{z_labels[z_index]}_{x_labels[x_index]}_leg"
            else:
                name = f"{z_labels[z_index]}_{x_labels[x_index]}_support"
            parts.append(
                _proposal(
                    name,
                    "leg",
                    region,
                    (z_span[1] - z_span[0]) / side.object_width * depth,
                    z_span[0] / side.object_width * depth,
                    order,
                    0.56,
                    ["front", "back", "left", "right"],
                )
            )
            order += 1
    if len(front_spans) == 2 and len(depth_spans) == 2:
        front_apron_band = _table_apron_band(front, top_stop)
        if front_apron_band is not None:
            apron_start, apron_stop = front_apron_band
            apron = remap_vertical(
                trace_region(
                    front,
                    front_spans[0][1],
                    apron_start,
                    front_spans[1][0],
                    apron_stop,
                    width,
                    height,
                ),
                vertical_scale,
            )
            for label, span in zip(("front", "rear"), depth_spans, strict=True):
                parts.append(
                    _proposal(
                        f"{label}_apron",
                        "panel",
                        apron,
                        (span[1] - span[0]) / side.object_width * depth,
                        span[0] / side.object_width * depth,
                        order,
                        0.52,
                        ["front", "back", "left", "right"],
                    )
                )
                order += 1
        # Side evidence is independent: a table can have side aprons without
        # front/rear ones, and their height need not match the front apron.
        side_apron_band = _table_apron_band(side, side_start)
        inner_depth_start = depth_spans[0][1]
        inner_depth_stop = depth_spans[1][0]
        if side_apron_band is not None and inner_depth_stop > inner_depth_start:
            side_vertical_scale = (
                side.object_height / max(1, side.object_height - side_start)
                * underside_height / height
            )
            side_region = remap_vertical(
                trace_region(
                    side, inner_depth_start, side_apron_band[0],
                    inner_depth_stop, side_apron_band[1], depth, height,
                ),
                side_vertical_scale,
            )
            for label, span in zip(("left", "right"), front_spans, strict=True):
                side_apron = _rectangle_region(
                    (span[1] - span[0]) / front.object_width * width,
                    side_region.height,
                    span[0] / front.object_width * width,
                    side_region.y,
                )
                parts.append(
                    _proposal(
                        f"{label}_apron", "panel", side_apron,
                        side_region.width, side_region.x, order, 0.48,
                        ["left", "right", "front", "back"],
                    )
                )
                order += 1
    return parts, [
        "Hidden joinery and the tabletop underside are inferred; verify them in the part editor",
        "Tabletop thickness is estimated because camera perspective makes its front-view height unreliable",
        "Apron depth and rear-leg placement are estimated from opposite views; correct them against the photographs",
        "Front/back and left/right labels assume the photographs were placed in the requested slots",
    ]


def _dense_bands(values: list[float], threshold: float) -> list[tuple[int, int]]:
    return _spans(
        values, threshold, gap=1, minimum=max(2, len(values) // 100)
    )


def _coherent_photo_edges(
    view: AnalyzedView, *, vertical: bool = False,
) -> list[tuple[int, float]]:
    """Long same-sign grayscale boundaries, not merely foreground occupancy."""
    left, top, _, _ = view.bbox
    along = view.object_width if vertical else view.object_height
    across = view.object_height if vertical else view.object_width
    start, stop = round(across * 0.15), round(across * 0.85)
    edges: list[tuple[int, float]] = []
    last_position = -10
    for position in range(1, along):
        changes = []
        for cross in range(start, stop):
            x, y = (position, cross) if vertical else (cross, position)
            index = (top + y) * view.width + left + x
            previous = index - (1 if vertical else view.width)
            # Exclude edges belonging to background labels or empty openings.
            if view.mask[index] and view.mask[previous]:
                changes.append(view.grayscale[index] - view.grayscale[previous])
        if len(changes) < (stop - start) * 0.8:
            continue
        contrast = median(changes)
        if abs(contrast) < 16:
            continue
        direction = 1 if contrast > 0 else -1
        if sum(change * direction >= 9 for change in changes) < len(changes) * 0.7:
            continue
        if edges and position - last_position <= 3 and contrast * edges[-1][1] > 0:
            if abs(contrast) > abs(edges[-1][1]):
                edges[-1] = (position, contrast)
        else:
            edges.append((position, contrast))
        last_position = position
    return edges


def _bookshelf_edge_bands(
    front: AnalyzedView, edges: list[tuple[int, float]],
    *, low: float = 0.07, high: float = 0.93,
) -> list[tuple[int, int]]:
    """Pair sustained opposite edges of thin shelf faces; suppress shadow pairs."""
    maximum = max(3, round(front.object_height * 0.04))
    candidates = [
        (abs(first[1]) + abs(second[1]), first[0], second[0])
        for first, second in zip(edges, edges[1:])
        if first[1] * second[1] < 0
        and 2 <= second[0] - first[0] <= maximum
        and first[0] > front.object_height * low
        and second[0] < front.object_height * high
    ]
    bands: list[tuple[int, int]] = []
    for _, start, stop in sorted(candidates, reverse=True):
        # One face can have several shadows/texture edges. Keep its strongest
        # pair, not an extra shelf on each side of the same highlight.
        if all(stop + maximum < other_start or start - maximum > other_stop
               for other_start, other_stop in bands):
            bands.append((start, stop))
    return sorted(bands)


def _backed_bookshelf(
    front: AnalyzedView, width: float, height: float, depth: float,
) -> tuple[list[PartProposal], list[str]]:
    edges = _coherent_photo_edges(front)
    shelves = _bookshelf_edge_bands(front, edges)
    if not shelves:
        raise ValueError(
            "No reliable internal shelf boundaries were found in the backed "
            "bookshelf photo. Use a clear, straight-on empty front view; "
            "WUE will not insert a guessed middle shelf."
        )
    # Use persistent central-row bounds rather than a shadow-expanded bottom
    # bounding box when locating the outer side faces.
    left, top, _, _ = front.bbox
    spans = []
    for y in range(round(front.object_height * 0.2), round(front.object_height * 0.8)):
        occupied = [x for x in range(front.object_width)
                    if front.mask[(top + y) * front.width + left + x]]
        if len(occupied) >= front.object_width * 0.6:
            spans.append((occupied[0], occupied[-1] + 1))
    if not spans:
        raise ValueError("The bookshelf outer frame could not be separated reliably")
    outer_left = round(median(span[0] for span in spans))
    outer_right = round(median(span[1] for span in spans))
    span_width = outer_right - outer_left
    vertical = _coherent_photo_edges(front, vertical=True)
    side_edges = []
    for low, high in ((outer_left + 3, outer_left + span_width * 0.12),
                      (outer_right - span_width * 0.12, outer_right - 3)):
        candidates = [edge for edge in vertical if low <= edge[0] <= high]
        if not candidates:
            raise ValueError("The bookshelf side-panel boundaries need a clearer front view")
        side_edges.append(max(candidates, key=lambda edge: abs(edge[1]))[0])
    interior_left, interior_right = side_edges
    face_height = round(median(stop - start for start, stop in shelves))
    cap_edges = [edge for edge in edges if 3 <= edge[0] < front.object_height * 0.07]
    top_stop = (max(cap_edges, key=lambda edge: abs(edge[1]))[0]
                if cap_edges else face_height)
    # A terminal shelf can blend into the floor/shadow; use its visible face
    # onset if present and the observed shelf-face thickness as a provisional
    # estimate. Never interpret a narrow leg remnant as the whole bottom panel.
    polarity = next(contrast for position, contrast in edges if position == shelves[-1][0])
    bottom_edges = [position for position, contrast in edges
                    if contrast * polarity > 0
                    and shelves[-1][1] + front.object_height * 0.05 < position
                    < front.object_height * 0.95]
    bottom_start = max(bottom_edges) if bottom_edges else front.object_height - face_height
    bottom_stop = min(front.object_height, bottom_start + face_height)
    # Prefer an independently observed terminal face over copying the median
    # interior shelf thickness. The pair must lie below all interior shelves,
    # have the same onset polarity, and retain foreground on both boundaries;
    # floor/background transitions are deliberately not treated as timber.
    terminal_bands = _bookshelf_edge_bands(
        front, edges,
        low=(shelves[-1][1] / front.object_height + 0.05), high=0.99,
    )
    terminal_bands = [band for band in terminal_bands
                      if any(position == band[0] and contrast * polarity > 0
                             for position, contrast in edges)]
    measured_bottom = next((band for band in terminal_bands if band[0] == bottom_start), None)
    if measured_bottom is not None:
        bottom_start, bottom_stop = measured_bottom

    def region(x_start: int, y_start: int, x_stop: int, y_stop: int) -> TracedRegion:
        return _rectangle_region(
            (x_stop - x_start) / span_width * width,
            (y_stop - y_start) / front.object_height * height,
            (x_start - outer_left) / span_width * width,
            (front.object_height - y_stop) / front.object_height * height,
        )

    parts = [
        _proposal("left_side", "panel", region(outer_left, 0, interior_left, front.object_height),
                  depth, 0, 0, 0.5, ["front"]),
        _proposal("right_side", "panel", region(interior_right, 0, outer_right, front.object_height),
                  depth, 0, 1, 0.5, ["front"]),
        _proposal("top_panel", "panel", region(interior_left, 0, interior_right, top_stop),
                  depth, 0, 2, 0.48, ["front"]),
        _proposal("bottom_panel", "panel", region(interior_left, bottom_start, interior_right, bottom_stop),
                  depth, 0, 3, 0.4, ["front"]),
        _proposal("back_panel", "panel", region(interior_left, top_stop, interior_right, bottom_start),
                  max(depth * 0.035, 1), depth * 0.965, 4, 0.35, ["front"]),
    ]
    for number, (start, stop) in enumerate(shelves, start=1):
        parts.append(_proposal(
            f"shelf_{number}", "panel", region(interior_left, start, interior_right, stop),
            depth * 0.94, 0, 4 + number, 0.5, ["front"],
        ))
    warnings = [
        "Shelf faces were proposed from long internal contrast edges, not the outer silhouette; review each boundary",
        "Bookshelf panel depth, back thickness and hidden joints remain provisional; side/back views have not independently fitted them",
        "Perspective and floor shadows can distort the frame scale; confirm dimensions before finalizing",
    ]
    if measured_bottom is None:
        warnings.append(
            "Bottom-panel thickness is provisional: its lower face boundary was not separated; "
            "the median visible interior shelf-face thickness was reused"
        )
    else:
        warnings.append(
            "Bottom-panel thickness uses its own visible front-face edge pair, not an interior shelf; "
            "it is a projected estimate, not a physical measurement"
        )
    if not cap_edges:
        warnings.append(
            "Top-panel thickness is provisional: no reliable cap boundary was found; "
            "the median visible interior shelf-face thickness was reused"
        )
    else:
        warnings.append(
            "Top-panel thickness uses the front cap boundary; perspective can exaggerate its physical thickness"
        )
    if not bottom_edges:
        warnings.append("Bottom-panel position is provisional: no reliable terminal face onset was found")
    return parts, warnings


def _bookshelf(
    views: dict[str, AnalyzedView], width: float, height: float, depth: float
) -> tuple[list[PartProposal], list[str]]:
    front = views["front"]
    if front.fill_ratio > 0.75:
        return _backed_bookshelf(front, width, height, depth)
    columns = front.columns()
    rows = front.rows()
    vertical = _dense_bands(columns, 0.72)
    horizontal = _dense_bands(rows, 0.68)
    if len(vertical) < 2:
        edge = max(2, round(front.object_width * 0.04))
        vertical = [(0, edge), (front.object_width - edge, front.object_width)]
    else:
        vertical = [vertical[0], vertical[-1]]
    if len(horizontal) < 2:
        edge = max(2, round(front.object_height * 0.04))
        horizontal = [
            (0, edge),
            (front.object_height - edge, front.object_height),
        ]
    horizontal = sorted(horizontal)
    top_band, bottom_band = horizontal[0], horizontal[-1]
    parts: list[PartProposal] = []
    for order, (name, span) in enumerate(
        (("left_side", vertical[0]), ("right_side", vertical[-1]))
    ):
        region = trace_region(
            front, span[0], 0, span[1], front.object_height, width, height
        )
        parts.append(
            _proposal(
                name,
                "panel",
                region,
                depth,
                0,
                order,
                0.62,
                ["front", "back", "top"],
            )
        )
    for name, span, order in (
        ("top_panel", top_band, 2),
        ("bottom_panel", bottom_band, 3),
    ):
        region = trace_region(
            front,
            vertical[0][1],
            span[0],
            vertical[-1][0],
            span[1],
            width,
            height,
        )
        parts.append(
            _proposal(
                name,
                "panel",
                region,
                depth,
                0,
                order,
                0.62,
                ["front", "back", "left", "right"],
            )
        )
    interior_x_start, interior_x_stop = vertical[0][1], vertical[-1][0]
    interior_y_start, interior_y_stop = top_band[1], bottom_band[0]
    back = trace_region(
        front,
        interior_x_start,
        interior_y_start,
        interior_x_stop,
        interior_y_stop,
        width,
        height,
    )
    parts.append(
        _proposal(
            "back_panel",
            "panel",
            back,
            max(depth * 0.035, 1),
            depth * 0.965,
            4,
            0.46,
            ["back"],
        )
    )
    shelves = [
        band
        for band in horizontal[1:-1]
        if band[0] > interior_y_start and band[1] < interior_y_stop
    ]
    if not shelves:
        raise ValueError(
            "No reliable shelf bands were found. WUE will not insert a guessed middle shelf; "
            "use an unobstructed front photo with visible shelf boundaries."
        )
    for number, span in enumerate(shelves, start=1):
        region = trace_region(
            front,
            interior_x_start,
            span[0],
            interior_x_stop,
            span[1],
            width,
            height,
        )
        parts.append(
            _proposal(
                f"shelf_{number}",
                "panel",
                region,
                depth * 0.94,
                0,
                4 + number,
                0.55,
                ["front", "back", "left", "right"],
            )
        )
    return parts, [
        "The back panel and any shelf hidden by objects are low-confidence inferences",
        "Remove books and decorations before photographing for the cleanest shelf detection",
    ]


def reconstruct(
    furniture_type: str,
    views: dict[str, AnalyzedView],
    width: float,
    height: float,
    depth: float,
    input_warnings: list[str],
    provider_name: str = "wue-five-view-silhouette",
    provider_version: str = "0.3.0",
    pipeline_warning: str = (
        "This local pipeline traces real silhouettes but does not yet run SAM 2 "
        "or dense multi-view depth"
    ),
) -> ReconstructionResponse:
    builders = {
        "chair": _chair,
        "dining_table": _dining_table,
        "bookshelf": _bookshelf,
    }
    parts, warnings = builders[furniture_type](views, width, height, depth)
    photographed_aspect = views["front"].object_width / views["front"].object_height
    supplied_aspect = width / height
    aspect_conflict = max(
        photographed_aspect / supplied_aspect,
        supplied_aspect / photographed_aspect,
    )
    if aspect_conflict > 2:
        warnings.insert(
            0,
            "Supplied width and height strongly disagree with the front photo's "
            "proportions; check the overall measurements before finalizing",
        )
    quality = sum(
        min(1.0, view.dominance) for view in views.values()
    ) / len(views)
    confidence = min(0.72, max(0.35, quality * 0.68))
    return ReconstructionResponse(
        provider_name=provider_name,
        provider_version=provider_version,
        confidence=round(confidence, 3),
        warnings=[
            pipeline_warning,
            *(
                view.segmentation_warning
                for view in views.values()
                if view.segmentation_warning
            ),
            *input_warnings,
            *warnings,
        ],
        parts=parts,
    )


def _structure_candidates(views: dict[str, AnalyzedView]) -> set[str]:
    """Conservative support gate, not open-world semantic object recognition.

    Require an observed support/opening pattern rather than choosing a type
    merely because it scored highest. Clear furniture-like impostors can still
    pass; unfamiliar or occluded supported furniture can be rejected.
    """
    def legged(view: AnalyzedView) -> bool:
        spans = _spans(view.columns(round(view.object_height * .74), round(view.object_height * .94)),
                       .45, gap=1, minimum=max(2, view.object_width // 100))
        # Perspective can expose three/four legs, not just two front legs.
        return (2 <= len(spans) <= 4
                and max(second[0] - first[1] for first, second in zip(spans, spans[1:])) >= view.object_width * .2
                and sum(stop - start for start, stop in spans) <= view.object_width * .65)

    def broad_bands(view: AnalyzedView) -> list[tuple[int, int]]:
        return _dense_bands(view.rows(), .65)

    def chair_elevation(view: AnalyzedView, side: bool) -> bool:
        bands = broad_bands(view)
        height = view.object_height
        seat = (any(.28 * height <= (start + stop) / 2 <= .72 * height
                    and stop - start <= height * .28 for start, stop in bands) if side
                else max(view.rows()[round(height * .3):round(height * .7)]) >= .65)
        upper = view.rows()[round(height * .10):round(height * .28)]
        occupancy = sum(upper) / max(1, len(upper))
        return (legged(view) and seat and len(bands) <= 2
                and (.04 <= occupancy <= .5 if side else occupancy >= .12))

    def table_elevation(view: AnalyzedView) -> bool:
        height = view.object_height
        bands = broad_bands(view)
        return (legged(view) and len(bands) == 1
                and bands[0][0] < height * .08 and bands[0][1] <= height * .45)

    def framed(view: AnalyzedView) -> bool:
        columns = view.columns(round(view.object_height * .12), round(view.object_height * .88))
        edge = max(2, round(len(columns) * .18))
        return max(columns[:edge]) >= .7 and max(columns[-edge:]) >= .7

    candidates = set()
    if all(chair_elevation(views[name], name in {"left", "right"})
           for name in ("front", "back", "left", "right")):
        candidates.add("chair")
    if all(table_elevation(views[name]) for name in ("front", "back", "left", "right")):
        candidates.add("dining_table")
    front = views["front"]
    bands = broad_bands(front)
    open_shelves = (len(bands) >= 3 and any(.08 * front.object_height < start
                    and stop < .92 * front.object_height for start, stop in bands))
    backed_shelves = bool(_bookshelf_edge_bands(front, _coherent_photo_edges(front)))
    if (open_shelves or backed_shelves) and all(framed(views[name]) for name in ("front", "left", "right")):
        candidates.add("bookshelf")
    return candidates


def classify(views: dict[str, AnalyzedView]) -> tuple[str, float]:
    candidates = _structure_candidates(views)
    if len(candidates) != 1:
        raise ValueError(
            "Unsupported or uncertain furniture: WUE could not establish a clear chair, dining table, or bookshelf structure. "
            "Upload five clear views of one supported furniture piece with its seat/backrest, tabletop/legs, or shelves visible."
        )
    front = views["front"]
    rows = front.rows()
    columns = front.columns()
    height = len(rows)
    width = len(columns)
    upper = sum(rows[: max(1, height // 3)]) / max(1, height // 3)
    lower_start = height * 2 // 3
    fill = front.fill_ratio
    aspect = front.object_width / front.object_height
    lower_spans = len(
        _spans(
            front.columns(lower_start, height),
            0.12,
            gap=max(1, width // 60),
            minimum=2,
        )
    )
    full_height_columns = sum(value > 0.78 for value in columns) / max(1, width)
    horizontal_bands = len(_dense_bands(rows, 0.68))
    scores = {
        "bookshelf": 1.8 * fill
        + 1.0 * full_height_columns
        + 0.35 * min(horizontal_bands, 6),
        "dining_table": 0.9 * min(aspect, 2.5)
        + 0.8 * max(rows[: max(1, height // 2)])
        + 0.25 * lower_spans
        - 0.6 * upper,
        "chair": 0.9 * upper
        + 0.45 * lower_spans
        + 0.35 * (1 - fill)
        + 0.25 * (1 / max(aspect, 0.35)),
    }
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best = next(iter(candidates))
    # Legacy silhouette scores remain a heuristic display score, not the
    # acceptance gate and not a calibrated probability. Structural evidence
    # can disambiguate, for example, a table with a deep apron from a chair.
    margin = scores[best] - max(score for name, score in ordered if name != best)
    confidence = min(0.84, max(0.46, 0.54 + margin * 0.18))
    return best, round(confidence, 3)
