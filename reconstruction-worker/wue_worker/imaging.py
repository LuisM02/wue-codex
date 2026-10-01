"""Small, dependency-light silhouette analysis used by the first local worker."""

from __future__ import annotations

import hashlib
import math
from collections import deque
from dataclasses import dataclass
from io import BytesIO
from statistics import median

from PIL import Image, ImageOps, UnidentifiedImageError

from .segmentation import SegmentationProvider

REQUIRED_VIEWS = ("front", "back", "left", "right", "top")
MAX_ANALYSIS_EDGE = 448


class ImageSetRejected(ValueError):
    """Raised when the inputs do not contain five useful, coherent silhouettes."""


def _image_pixels(image: Image.Image) -> list:
    """Use Pillow's current flat-pixel API while retaining Pillow 11 support."""
    current_getter = getattr(image, "get_flattened_data", None)
    return list(current_getter() if current_getter else image.getdata())


@dataclass(frozen=True, slots=True)
class AnalyzedView:
    name: str
    width: int
    height: int
    mask: bytes
    bbox: tuple[int, int, int, int]
    object_pixels: int
    foreground_pixels: int
    checksum_sha256: str
    grayscale: bytes
    segmentation_warning: str | None = None

    @property
    def object_width(self) -> int:
        return self.bbox[2] - self.bbox[0]

    @property
    def object_height(self) -> int:
        return self.bbox[3] - self.bbox[1]

    @property
    def fill_ratio(self) -> float:
        return self.object_pixels / max(1, self.object_width * self.object_height)

    @property
    def dominance(self) -> float:
        return self.object_pixels / max(1, self.foreground_pixels)

    def rows(self) -> list[float]:
        left, top, right, bottom = self.bbox
        width = right - left
        return [
            sum(self.mask[y * self.width + left : y * self.width + right]) / max(1, width)
            for y in range(top, bottom)
        ]

    def columns(self, start_y: int = 0, end_y: int | None = None) -> list[float]:
        left, top, right, bottom = self.bbox
        start = top + max(0, start_y)
        stop = top + min(bottom - top, end_y if end_y is not None else bottom - top)
        height = max(1, stop - start)
        return [
            sum(self.mask[y * self.width + x] for y in range(start, stop)) / height
            for x in range(left, right)
        ]


def _percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    if not ordered:
        return 0
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * fraction))]


def _largest_component(raw: bytearray, width: int, height: int) -> tuple[bytearray, int]:
    visited = bytearray(width * height)
    best: list[int] = []
    for start, value in enumerate(raw):
        if not value or visited[start]:
            continue
        queue: deque[int] = deque([start])
        visited[start] = 1
        component: list[int] = []
        while queue:
            index = queue.popleft()
            component.append(index)
            x = index % width
            for neighbor in (index - width, index + width, index - 1, index + 1):
                if neighbor < 0 or neighbor >= len(raw) or visited[neighbor] or not raw[neighbor]:
                    continue
                if neighbor == index - 1 and x == 0:
                    continue
                if neighbor == index + 1 and x == width - 1:
                    continue
                visited[neighbor] = 1
                queue.append(neighbor)
        if len(component) > len(best):
            best = component
    result = bytearray(width * height)
    for index in best:
        result[index] = 1
    return result, len(best)


def _clean_mask(raw: bytearray, width: int, height: int) -> bytearray:
    cleaned = bytearray(raw)
    for y in range(1, height - 1):
        row = y * width
        for x in range(1, width - 1):
            index = row + x
            neighbors = sum(
                raw[index + dy * width + dx]
                for dy in (-1, 0, 1)
                for dx in (-1, 0, 1)
            )
            cleaned[index] = 1 if neighbors >= (4 if raw[index] else 6) else 0
    return cleaned


def _neural_mask_fills_open_space(
    seed_pixels: int,
    seed_bbox: tuple[int, int, int, int],
    refined: bytearray,
    width: int,
    height: int,
) -> bool:
    """Keep a clear foreground silhouette when a box prompt floods its openings."""
    refined_pixels = sum(refined)
    left, top, right, bottom = seed_bbox
    seed_area = max(1, (right - left) * (bottom - top))
    if seed_pixels / seed_area >= 0.65 or refined_pixels <= seed_pixels * 1.6:
        return False
    indices = [index for index, value in enumerate(refined) if value]
    if not indices:
        return False
    xs = [index % width for index in indices]
    ys = [index // width for index in indices]
    refined_area = (max(xs) - min(xs) + 1) * (max(ys) - min(ys) + 1)
    # A mask can also absorb the floor/shadow without becoming a solid box.
    # Large expansion around an already clear sparse seed is not reliable.
    return refined_pixels / refined_area >= 0.70 or refined_area > seed_area * 1.35


def analyze_image(
    name: str,
    data: bytes,
    segmentation: SegmentationProvider | None = None,
) -> AnalyzedView:
    try:
        with Image.open(BytesIO(data)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageSetRejected(f"The {name} file is not a readable image") from exc
    if image.width < 48 or image.height < 48:
        raise ImageSetRejected(f"The {name} image is too small for shape analysis")
    image.thumbnail((MAX_ANALYSIS_EDGE, MAX_ANALYSIS_EDGE), Image.Resampling.LANCZOS)
    width, height = image.size
    pixels = _image_pixels(image)
    step = max(1, min(width, height) // 80)
    border_indices = {
        y * width + x
        for x in range(0, width, step)
        for y in (0, height - 1)
    } | {
        y * width + x
        for y in range(0, height, step)
        for x in (0, width - 1)
    }
    border = [pixels[index] for index in border_indices]
    background = tuple(int(median(channel)) for channel in zip(*border, strict=True))
    border_distances = [
        max(abs(pixel[channel] - background[channel]) for channel in range(3))
        for pixel in border
    ]
    threshold = max(24, min(72, _percentile(border_distances, 0.75) + 18))
    raw = bytearray(
        1
        if max(abs(pixel[channel] - background[channel]) for channel in range(3)) >= threshold
        else 0
        for pixel in pixels
    )
    foreground_pixels = sum(raw)
    cleaned = _clean_mask(raw, width, height)
    mask, object_pixels = _largest_component(cleaned, width, height)
    if object_pixels < width * height * 0.012:
        raise ImageSetRejected(
            f"No clear furniture-sized foreground object was found in the {name} view"
        )
    seed_indices = [index for index, value in enumerate(mask) if value]
    seed_xs = [index % width for index in seed_indices]
    seed_ys = [index // width for index in seed_indices]
    seed_bbox = (min(seed_xs), min(seed_ys), max(seed_xs) + 1, max(seed_ys) + 1)
    segmentation_warning = None
    if segmentation is not None:
        seed_mask = bytes(mask)
        refined = segmentation.refine_mask(name, image, seed_mask, seed_bbox)
        if len(refined) != width * height:
            raise ImageSetRejected(
                f"The segmentation provider returned an invalid {name} mask"
            )
        if refined != seed_mask:
            refined_mask, refined_pixels = _largest_component(
                _clean_mask(bytearray(refined), width, height), width, height
            )
            if refined_pixels < width * height * 0.012:
                raise ImageSetRejected(
                    f"No clear furniture-sized foreground object was found in the {name} view"
                )
            if not _neural_mask_fills_open_space(
                object_pixels, seed_bbox, refined_mask, width, height
            ):
                mask, object_pixels = refined_mask, refined_pixels
            else:
                segmentation_warning = (
                    f"The neural mask filled open space in the {name} view; "
                    "the clearer foreground silhouette was used instead"
                )
    indices = [index for index, value in enumerate(mask) if value]
    xs = [index % width for index in indices]
    ys = [index // width for index in indices]
    bbox = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
    object_width = bbox[2] - bbox[0]
    object_height = bbox[3] - bbox[1]
    area_ratio = object_pixels / (width * height)
    if area_ratio > 0.88 or object_width < 12 or object_height < 12:
        raise ImageSetRejected(
            f"The {name} view does not isolate one complete furniture object"
        )
    edge_contacts = sum(
        (
            bbox[0] <= 1,
            bbox[1] <= 1,
            bbox[2] >= width - 1,
            bbox[3] >= height - 1,
        )
    )
    if edge_contacts >= 3:
        raise ImageSetRejected(
            f"The furniture is cropped or the background is unclear in the {name} view"
        )
    grayscale = ImageOps.grayscale(image).tobytes()
    return AnalyzedView(
        name=name,
        width=width,
        height=height,
        mask=bytes(mask),
        bbox=bbox,
        object_pixels=object_pixels,
        foreground_pixels=foreground_pixels,
        checksum_sha256=hashlib.sha256(data).hexdigest(),
        grayscale=grayscale,
        segmentation_warning=segmentation_warning,
    )


def _normalized_mask(view: AnalyzedView, size: int = 64) -> Image.Image:
    left, top, right, bottom = view.bbox
    mask_image = Image.frombytes(
        "L", (view.width, view.height), bytes(255 * value for value in view.mask)
    )
    return mask_image.crop((left, top, right, bottom)).resize(
        (size, size), Image.Resampling.NEAREST
    )


def pair_similarity(first: AnalyzedView, second: AnalyzedView) -> float:
    first_pixels = _image_pixels(_normalized_mask(first))
    second_image = _normalized_mask(second)
    candidates = [
        _image_pixels(second_image),
        _image_pixels(ImageOps.mirror(second_image)),
    ]
    scores: list[float] = []
    for second_pixels in candidates:
        intersection = sum(
            bool(a) and bool(b)
            for a, b in zip(first_pixels, second_pixels, strict=True)
        )
        union = sum(
            bool(a) or bool(b)
            for a, b in zip(first_pixels, second_pixels, strict=True)
        )
        scores.append(intersection / max(1, union))
    return max(scores)


def validate_view_set(
    views: dict[str, AnalyzedView],
    dimensions: tuple[float, float, float] | None = None,
) -> list[str]:
    missing = [name for name in REQUIRED_VIEWS if name not in views]
    if missing:
        raise ImageSetRejected("Missing required views: " + ", ".join(missing))
    checksums = [views[name].checksum_sha256 for name in REQUIRED_VIEWS]
    if len(set(checksums)) != len(checksums):
        raise ImageSetRejected(
            "Each view must be a different photograph; duplicate image files were detected"
        )
    for first, second, label in (
        ("front", "back", "front/back"),
        ("left", "right", "left/right"),
    ):
        if pair_similarity(views[first], views[second]) < 0.16:
            raise ImageSetRejected(
                f"The {label} photographs do not appear to show the same object from opposite sides"
            )
    warnings: list[str] = []
    for name, view in views.items():
        if view.dominance < 0.52:
            warnings.append(
                f"The {name} background contains competing objects; verify its traced outline"
            )
        if view.fill_ratio < 0.12:
            warnings.append(
                f"The {name} silhouette is sparse; thin parts may need manual correction"
            )
    if dimensions is not None:
        overall_width, overall_height, overall_depth = dimensions
        expected = {
            "front": overall_width / overall_height,
            "back": overall_width / overall_height,
            "left": overall_depth / overall_height,
            "right": overall_depth / overall_height,
            "top": overall_width / overall_depth,
        }
        for name, ratio in expected.items():
            view = views[name]
            observed = view.object_width / view.object_height
            mismatch = abs(math.log(max(observed, 1e-6) / max(ratio, 1e-6)))
            if mismatch > math.log(4.0):
                raise ImageSetRejected(
                    f"The {name} photo proportions differ strongly from the entered "
                    "width, height and depth. Check the overall dimensions, labeled "
                    "view and camera angle. This check cannot determine which is wrong"
                )
            if mismatch > math.log(2.1):
                warnings.append(
                    f"The {name} perspective differs strongly from the supplied dimensions"
                )
    return warnings
