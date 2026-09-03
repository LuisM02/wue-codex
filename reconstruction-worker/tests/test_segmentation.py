"""Focused tests for optional segmentation-provider readiness."""

from PIL import Image

from wue_worker.segmentation import (
    BaselineSegmentationProvider,
    Sam2SegmentationProvider,
)


def test_baseline_preserves_seed_mask_without_optional_dependencies() -> None:
    provider = BaselineSegmentationProvider()
    seed = bytes((0, 1, 1, 0))

    result = provider.refine_mask(
        "front",
        Image.new("RGB", (2, 2)),
        seed,
        (0, 0, 2, 2),
    )

    assert result == seed
    assert provider.status.ready is True
    assert provider.status.loaded_checkpoints == ()


def test_sam2_is_honest_when_no_local_checkpoint_is_configured() -> None:
    provider = Sam2SegmentationProvider(
        checkpoint=None,
        model_config="configs/sam2.1/sam2.1_hiera_b+.yaml",
        device="auto",
    )

    status = provider.status

    assert status.ready is False
    assert status.uses_gpu is False
    assert status.loaded_checkpoints == ()
    assert "WUE_SAM2_CHECKPOINT" in status.limitations[0]


def test_sam2_prompt_uses_centered_furniture_frame() -> None:
    image = Image.new("RGB", (400, 500))

    assert Sam2SegmentationProvider._furniture_prompt_box("front", image) == (
        48,
        30,
        340,
        490,
    )
    assert Sam2SegmentationProvider._furniture_prompt_box("top", image) == (
        48,
        30,
        340,
        400,
    )
