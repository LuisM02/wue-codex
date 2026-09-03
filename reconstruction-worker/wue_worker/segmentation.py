"""Selectable foreground segmentation for the local reconstruction worker."""

from __future__ import annotations

import hashlib
import importlib.util
import os
from contextlib import ExitStack
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Protocol

from PIL import Image


class SegmentationUnavailable(RuntimeError):
    """Raised when a configured neural segmenter cannot safely run."""


@dataclass(frozen=True, slots=True)
class SegmentationStatus:
    ready: bool
    pipeline: str
    uses_gpu: bool
    loaded_checkpoints: tuple[str, ...]
    limitations: tuple[str, ...]


class SegmentationProvider(Protocol):
    provider_name: str
    provider_version: str
    classifier_name: str
    reconstruction_warning: str

    @property
    def status(self) -> SegmentationStatus: ...

    def refine_mask(
        self,
        image: Image.Image,
        seed_mask: bytes,
        seed_bbox: tuple[int, int, int, int],
    ) -> bytes: ...


class BaselineSegmentationProvider:
    """Preserve the dependency-light foreground mask used in version 0.1."""

    provider_name = "wue-five-view-silhouette"
    provider_version = "0.2.0"
    classifier_name = "wue-image-structure"
    reconstruction_warning = (
        "This local pipeline traces real silhouettes but does not yet run SAM 2 "
        "or dense multi-view depth"
    )

    @property
    def status(self) -> SegmentationStatus:
        return SegmentationStatus(
            ready=True,
            pipeline="five-view-silhouette-baseline",
            uses_gpu=False,
            loaded_checkpoints=(),
            limitations=(
                "Best with one furniture item against a plain contrasting background",
                "Semantic parts are inferred from traced silhouettes",
                "SAM 2 and dense multi-view depth are not loaded in this baseline",
            ),
        )

    def refine_mask(
        self,
        image: Image.Image,
        seed_mask: bytes,
        seed_bbox: tuple[int, int, int, int],
    ) -> bytes:
        del image, seed_bbox
        return seed_mask


class Sam2SegmentationProvider:
    """Lazy SAM 2.1 box-prompt adapter backed by an explicit local checkpoint."""

    provider_name = "wue-sam2.1-five-view"
    classifier_name = "wue-image-structure+sam2.1"
    reconstruction_warning = (
        "SAM 2.1 segments the photographed outlines; dense multi-view depth and "
        "neural part recognition are not loaded yet"
    )

    def __init__(
        self,
        checkpoint: str | None,
        model_config: str,
        device: str,
    ) -> None:
        self._checkpoint = Path(checkpoint).expanduser() if checkpoint else None
        self._model_config = model_config
        self._requested_device = device
        self._predictor = None
        self._checkpoint_sha256: str | None = None
        self._resolved_device: str | None = None
        self._lock = Lock()

    @property
    def provider_version(self) -> str:
        checkpoint_name = (
            self._checkpoint.stem[:48] if self._checkpoint is not None else "unconfigured"
        )
        digest = (
            f"/sha256:{self._checkpoint_sha256[:16]}"
            if self._checkpoint_sha256 is not None
            else ""
        )
        return f"0.2.0/{checkpoint_name}{digest}"

    def _missing_prerequisites(self) -> list[str]:
        missing = [
            package
            for package in ("torch", "numpy", "sam2")
            if importlib.util.find_spec(package) is None
        ]
        if self._checkpoint is None:
            missing.append("WUE_SAM2_CHECKPOINT")
        elif not self._checkpoint.is_file():
            missing.append("SAM 2 checkpoint file")
        if self._requested_device == "cuda" and "torch" not in missing:
            import torch

            if not torch.cuda.is_available():
                missing.append("CUDA runtime")
        return missing

    def _device(self) -> str:
        if self._resolved_device is not None:
            return self._resolved_device
        if self._requested_device != "auto":
            self._resolved_device = self._requested_device
            return self._resolved_device
        if importlib.util.find_spec("torch") is None:
            self._resolved_device = "cpu"
            return self._resolved_device
        import torch

        self._resolved_device = "cuda" if torch.cuda.is_available() else "cpu"
        return self._resolved_device

    @property
    def status(self) -> SegmentationStatus:
        missing = self._missing_prerequisites()
        loaded = ()
        if self._predictor is not None and self._checkpoint is not None:
            checkpoint = self._checkpoint.name
            if self._checkpoint_sha256 is not None:
                checkpoint += f" (sha256:{self._checkpoint_sha256[:16]})"
            loaded = (checkpoint,)
        limitations = [
            "SAM 2 receives the baseline furniture bounds as a box prompt",
            "Dense multi-view depth and neural part recognition are not loaded yet",
        ]
        if missing:
            limitations.insert(
                0,
                "SAM 2 is configured but unavailable: " + ", ".join(missing),
            )
        elif self._predictor is None:
            limitations.insert(0, "The configured checkpoint loads on first inference")
        return SegmentationStatus(
            ready=not missing,
            pipeline="sam2.1-box-prompt+five-view-structural-fitting",
            uses_gpu=not missing and self._device() == "cuda",
            loaded_checkpoints=loaded,
            limitations=tuple(limitations),
        )

    def _load_predictor(self):
        if self._predictor is not None:
            return self._predictor
        status = self.status
        if not status.ready or self._checkpoint is None:
            raise SegmentationUnavailable(status.limitations[0])
        try:
            from sam2.build_sam import build_sam2
            from sam2.sam2_image_predictor import SAM2ImagePredictor

            model = build_sam2(
                self._model_config,
                str(self._checkpoint),
                device=self._device(),
            )
            self._predictor = SAM2ImagePredictor(model)
            digest = hashlib.sha256()
            with self._checkpoint.open("rb") as checkpoint_file:
                for chunk in iter(lambda: checkpoint_file.read(1024 * 1024), b""):
                    digest.update(chunk)
            self._checkpoint_sha256 = digest.hexdigest()
        except Exception as exc:  # third-party model/runtime boundary
            raise SegmentationUnavailable(
                f"SAM 2 could not load ({type(exc).__name__})"
            ) from exc
        return self._predictor

    def refine_mask(
        self,
        image: Image.Image,
        seed_mask: bytes,
        seed_bbox: tuple[int, int, int, int],
    ) -> bytes:
        del seed_mask
        try:
            with self._lock, ExitStack() as stack:
                predictor = self._load_predictor()
                import numpy as np
                import torch

                stack.enter_context(torch.inference_mode())
                if self._device() == "cuda":
                    stack.enter_context(torch.autocast("cuda", dtype=torch.bfloat16))
                predictor.set_image(np.asarray(image))
                masks, scores, _ = predictor.predict(
                    box=np.asarray(seed_bbox, dtype=np.float32),
                    multimask_output=True,
                )
                best = int(np.argmax(scores))
                if float(scores[best]) < 0.35:
                    raise SegmentationUnavailable(
                        "SAM 2 could not isolate the furniture confidently"
                    )
                mask = np.asarray(masks[best], dtype=np.bool_)
                if mask.shape != (image.height, image.width):
                    raise SegmentationUnavailable(
                        "SAM 2 returned a mask with unexpected dimensions"
                    )
                return bytes(mask.reshape(-1).astype(np.uint8).tolist())
        except SegmentationUnavailable:
            raise
        except Exception as exc:  # third-party inference/runtime boundary
            raise SegmentationUnavailable(
                f"SAM 2 inference failed ({type(exc).__name__})"
            ) from exc


def _configured_provider() -> str:
    value = os.getenv("WUE_WORKER_SEGMENTATION_PROVIDER", "baseline").strip().lower()
    if value not in {"baseline", "sam2"}:
        raise SegmentationUnavailable(
            "WUE_WORKER_SEGMENTATION_PROVIDER must be baseline or sam2"
        )
    return value


@lru_cache(maxsize=1)
def get_segmentation_provider() -> SegmentationProvider:
    if _configured_provider() == "baseline":
        return BaselineSegmentationProvider()
    device = os.getenv("WUE_SAM2_DEVICE", "auto").strip().lower()
    if device not in {"auto", "cuda", "cpu"}:
        raise SegmentationUnavailable("WUE_SAM2_DEVICE must be auto, cuda, or cpu")
    return Sam2SegmentationProvider(
        checkpoint=os.getenv("WUE_SAM2_CHECKPOINT"),
        model_config=os.getenv(
            "WUE_SAM2_MODEL_CONFIG",
            "configs/sam2.1/sam2.1_hiera_b+.yaml",
        ),
        device=device,
    )
