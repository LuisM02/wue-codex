"""Turn analyzed five-view silhouettes into editable, measured part proposals."""

from __future__ import annotations

from dataclasses import dataclass

from .imaging import AnalyzedView
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


def _chair(
    views: dict[str, AnalyzedView], width: float, height: float, depth: float
) -> tuple[list[PartProposal], list[str]]:
    front, side = views["front"], views["left"]
    seat_top, seat_bottom, seat_center = _strongest_band(front, 0.38, 0.72)
    side_center = round(seat_center / front.object_height * side.object_height)
    side_half_band = max(
        2,
        round(
            (seat_bottom - seat_top)
            / front.object_height
            * side.object_height
        ),
    )
    seat = trace_region(
        front,
        0,
        seat_top,
        front.object_width,
        seat_bottom,
        width,
        height,
    )
    seat_depth, seat_z = _depth_geometry(
        side,
        max(0, side_center - side_half_band),
        min(side.object_height, side_center + side_half_band),
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
    backrest = trace_region(
        front, 0, 0, front.object_width, seat_top, width, height
    )
    back_depth, back_z = _depth_geometry(
        side,
        0,
        max(2, round(seat_top / front.object_height * side.object_height)),
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

    front_spans = _leg_regions(front, seat_bottom)
    side_start = min(
        side.object_height - 1,
        round(seat_bottom / front.object_height * side.object_height),
    )
    depth_spans = _leg_regions(side, side_start)
    order = 2
    front_labels = ["left", "right"] if len(front_spans) == 2 else ["center"]
    depth_labels = ["front", "rear"] if len(depth_spans) == 2 else ["center"]
    for depth_index, depth_span in enumerate(depth_spans):
        for front_index, front_span in enumerate(front_spans):
            region = trace_region(
                front,
                front_span[0],
                seat_bottom,
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
    warnings = [
        "Hidden joinery and occluded rear surfaces are inferred; verify them in the part editor",
        "Front/back and left/right labels assume the photographs were placed in the requested slots",
    ]
    return parts, warnings


def _dining_table(
    views: dict[str, AnalyzedView], width: float, height: float, depth: float
) -> tuple[list[PartProposal], list[str]]:
    front, side = views["front"], views["left"]
    top_start, top_stop, _ = _strongest_band(front, 0.02, 0.42)
    tabletop = trace_region(
        front, 0, top_start, front.object_width, top_stop, width, height
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
    front_spans = _leg_regions(front, top_stop)
    side_start = min(
        side.object_height - 1,
        round(top_stop / front.object_height * side.object_height),
    )
    depth_spans = _leg_regions(side, side_start)
    order = 1
    x_labels = ["left", "right"] if len(front_spans) == 2 else ["center"]
    z_labels = ["front", "rear"] if len(depth_spans) == 2 else ["center"]
    for z_index, z_span in enumerate(depth_spans):
        for x_index, x_span in enumerate(front_spans):
            region = trace_region(
                front,
                x_span[0],
                top_stop,
                x_span[1],
                front.object_height,
                width,
                height,
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
    return parts, [
        "Hidden joinery and the tabletop underside are inferred; verify them in the part editor",
        "Front/back and left/right labels assume the photographs were placed in the requested slots",
    ]


def _dense_bands(values: list[float], threshold: float) -> list[tuple[int, int]]:
    return _spans(
        values, threshold, gap=1, minimum=max(2, len(values) // 100)
    )


def _bookshelf(
    views: dict[str, AnalyzedView], width: float, height: float, depth: float
) -> tuple[list[PartProposal], list[str]]:
    front = views["front"]
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
        center = round((interior_y_start + interior_y_stop) / 2)
        thickness = max(2, round(front.object_height * 0.025))
        shelves = [(center, min(interior_y_stop, center + thickness))]
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
    provider_version: str = "0.2.0",
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
            *input_warnings,
            *warnings,
        ],
        parts=parts,
    )


def classify(views: dict[str, AnalyzedView]) -> tuple[str, float]:
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
    best, best_score = ordered[0]
    margin = best_score - ordered[1][1]
    confidence = min(0.84, max(0.46, 0.54 + margin * 0.18))
    return best, round(confidence, 3)
