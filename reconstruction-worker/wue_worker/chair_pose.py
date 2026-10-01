"""Conservative two-elevation projected lean, not physical camera calibration."""

from dataclasses import dataclass
from math import atan, cos, degrees, sin
from statistics import median

from .imaging import AnalyzedView
from .schemas import PartProposal, ProfilePoint


@dataclass(frozen=True, slots=True)
class LeanLine:
    slope: float  # canonical Z per Y; positive is rearward at increasing Y
    intercept: float


def _side_line(view: AnalyzedView, low: float, high: float, height: float, depth: float) -> LeanLine | None:
    start, stop = round(low * view.object_height), round(high * view.object_height)
    if stop - start < 12:
        return None
    left, top, _, _ = view.bbox
    samples = []
    widths = []
    for row in range(start, stop):
        offset = (top + row) * view.width + left
        occupied = [x for x in range(view.object_width) if view.mask[offset + x]]
        if len(occupied) < 3:
            continue
        # Adjacent overlapping posts/slats can form a single envelope. Widely
        # separated members/objects do not establish one backrest centerline.
        if any(b - a > max(3, view.object_width * .04) for a, b in zip(occupied, occupied[1:])):
            continue
        width = occupied[-1] + 1 - occupied[0]
        if width > view.object_width * .4:
            continue
        center = (occupied[0] + occupied[-1] + 1) / 2 / view.object_width
        if view.name == "left":
            center = 1 - center
        samples.append(((1 - (row + .5) / view.object_height) * height, center * depth))
        widths.append(width)
    if len(samples) < max(12, round((stop - start) * .8)):
        return None
    typical = median(widths)
    if min(widths) < typical * .65 or max(widths) > typical * 1.4:
        return None
    mean_y = sum(y for y, _ in samples) / len(samples)
    mean_z = sum(z for _, z in samples) / len(samples)
    variance = sum((y - mean_y) ** 2 for y, _ in samples)
    if variance <= 0:
        return None
    slope = sum((y - mean_y) * (z - mean_z) for y, z in samples) / variance
    intercept = mean_z - slope * mean_y
    residuals = sorted(abs(z - (slope * y + intercept)) for y, z in samples)
    if residuals[round((len(residuals) - 1) * .9)] > depth * max(.015, 2 / view.object_width):
        return None
    return LeanLine(slope, intercept)


def fit_backrest_lean(views: dict[str, AnalyzedView], low: float, high: float, height: float, depth: float) -> LeanLine | None:
    if not 0 <= low < high <= 1 or height <= 0 or depth <= 0:
        return None
    if any(name not in views or views[name].name != name for name in ("left", "right")):
        return None
    # Avoid cap/seat junctions, which can have a different silhouette width.
    margin = (high - low) * .15
    left = _side_line(views["left"], low + margin, high - margin, height, depth)
    right = _side_line(views["right"], low + margin, high - margin, height, depth)
    if left is None or right is None:
        return None
    angles = degrees(atan(left.slope)), degrees(atan(right.slope))
    if abs(angles[0] - angles[1]) > 2.5 or any(abs(angle) > 18 for angle in angles):
        return None
    # Check placement across the complete fitted interval, not just a midpoint.
    for y in ((1 - low) * height, (1 - high) * height):
        if abs((left.slope - right.slope) * y + left.intercept - right.intercept) > depth * .05:
            return None
    slope = (left.slope + right.slope) / 2
    if abs(degrees(atan(slope))) < .8:
        return None  # Do not add a cosmetic tilt to an effectively upright chair.
    return LeanLine(slope, (left.intercept + right.intercept) / 2)


def apply_backrest_lean(parts: list[PartProposal], line: LeanLine, height: float, depth: float) -> list[PartProposal] | None:
    angle = atan(line.slope)
    cosine, sine = cos(angle), sin(angle)
    result = []
    changed = False
    for part in parts:
        if part.component_name not in {"left_backrest_post", "right_backrest_post"} and not part.component_name.startswith("backrest_slat_"):
            result.append(part)
            continue
        # The old depth is a horizontal side-row envelope, not the member's
        # normal stock thickness. Preserve that cross-section and front-view
        # vertical bounding span when converting to a center-pivot extrusion.
        local_depth = part.depth * cosine
        local_height = (part.height - local_depth * abs(sine)) / cosine
        if local_height <= 0:
            return None
        center_y = part.y + part.height / 2
        center_z = line.slope * center_y + line.intercept
        half_z = (local_height * abs(sine) + local_depth * cosine) / 2
        if center_z - half_z < 0 or center_z + half_z > depth or part.y < 0 or part.y + part.height > height + .001:
            return None  # Reject the entire assembly; never clip/partially tilt it.
        def rounded(value: float) -> float:
            return round(value, 4)

        updated = part.model_copy(update={
            "height": rounded(local_height), "depth": rounded(local_depth),
            "y": rounded(center_y - local_height / 2), "z": rounded(center_z - local_depth / 2),
            "rotation_x": rounded(degrees(angle)),
            "profile_points": [ProfilePoint(u=p.u, v=min(rounded(local_height), rounded(p.v * local_height / part.height))) for p in part.profile_points] if part.profile_points else None,
        })
        result.append(PartProposal.model_validate(updated.model_dump()))
        changed = True
    return result if changed else None
