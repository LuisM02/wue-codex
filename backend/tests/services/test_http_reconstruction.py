"""Contract tests for the isolated local-AI HTTP connector."""

from decimal import Decimal

import httpx
import pytest

from app.core.enums import FurnitureImageView, FurnitureType
from app.services.dimensions import CanonicalDimensions
from app.services.http_reconstruction import HttpFurnitureReconstructor
from app.services.photo_reconstruction import (
    InvalidReconstructionOutputError,
    ReconstructionImage,
    ReconstructionInputRejectedError,
    ReconstructionProviderUnavailableError,
)


def inputs() -> tuple[ReconstructionImage, ...]:
    return tuple(
        ReconstructionImage(
            view=view,
            content_type="image/png",
            checksum_sha256=str(index) * 64,
            data=f"image-{view.value}".encode(),
        )
        for index, view in enumerate(FurnitureImageView, start=1)
    )


def dimensions() -> CanonicalDimensions:
    return CanonicalDimensions(
        width_mm=Decimal("800"),
        height_mm=Decimal("1000"),
        depth_mm=Decimal("600"),
    )


def test_posts_all_views_and_parses_structured_part_geometry() -> None:
    seen: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        body = request.read()
        assert request.url == "http://127.0.0.1:8010/v1/reconstruct"
        assert b'name="front"' in body
        assert b'image-front' in body
        assert b'name="furniture_type"' in body
        assert b"chair" in body
        return httpx.Response(
            200,
            json={
                "provider_name": "local-test-ai",
                "provider_version": "1",
                "confidence": 0.8,
                "warnings": [],
                "parts": [
                    {
                        "component_name": "seat",
                        "component_type": "panel",
                        "geometry_kind": "extruded_profile",
                        "profile_points": [
                            {"u": 0, "v": 0},
                            {"u": 700, "v": 0},
                            {"u": 650, "v": 50},
                        ],
                        "width": 700,
                        "height": 50,
                        "depth": 500,
                        "x": 50,
                        "y": 450,
                        "z": 50,
                        "source_views": ["front", "left", "right"],
                    }
                ],
            },
        )

    adapter = HttpFurnitureReconstructor(
        "http://127.0.0.1:8010/",
        30,
        transport=httpx.MockTransport(respond),
    )

    result = adapter.reconstruct(inputs(), FurnitureType.CHAIR, dimensions())

    assert len(seen) == 1
    assert result.provider_name == "local-test-ai"
    assert result.parts[0].geometry_kind.value == "extruded_profile"
    assert result.parts[0].profile_points is not None


def test_network_failure_is_reported_as_provider_unavailable() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    adapter = HttpFurnitureReconstructor(
        "http://127.0.0.1:8010",
        30,
        transport=httpx.MockTransport(fail),
    )

    with pytest.raises(
        ReconstructionProviderUnavailableError,
        match="local photo reconstruction service is unavailable",
    ):
        adapter.reconstruct(inputs(), FurnitureType.CHAIR, dimensions())


def test_worker_failure_preserves_safe_detail() -> None:
    adapter = HttpFurnitureReconstructor(
        "http://127.0.0.1:8010",
        30,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                503, json={"detail": "SAM 2 checkpoint could not load"}
            )
        ),
    )

    with pytest.raises(
        ReconstructionProviderUnavailableError,
        match="SAM 2 checkpoint could not load",
    ):
        adapter.reconstruct(inputs(), FurnitureType.CHAIR, dimensions())


@pytest.mark.parametrize("status", [400, 422])
def test_photo_rejection_preserves_reason_without_claiming_invalid_geometry(status):
    adapter = HttpFurnitureReconstructor("http://worker", 30, transport=httpx.MockTransport(
        lambda request: httpx.Response(status, json={"detail": "No reliable internal shelf boundaries were found"})
    ))
    with pytest.raises(ReconstructionInputRejectedError, match="internal shelf boundaries"):
        adapter.reconstruct(inputs(), FurnitureType.BOOKSHELF, dimensions())


@pytest.mark.parametrize("status", [401, 403, 404, 408, 429])
def test_worker_configuration_or_busy_status_is_not_a_photo_rejection(status):
    adapter = HttpFurnitureReconstructor("http://worker", 30, transport=httpx.MockTransport(
        lambda request: httpx.Response(status, json={"detail": "Internal routing detail"})
    ))
    with pytest.raises(ReconstructionProviderUnavailableError, match="could not accept the request"):
        adapter.reconstruct(inputs(), FurnitureType.CHAIR, dimensions())


@pytest.mark.parametrize("payload", [{"detail": []}, {"detail": "  "}, {}])
def test_malformed_rejection_is_an_invalid_worker_result(payload):
    adapter = HttpFurnitureReconstructor("http://worker", 30, transport=httpx.MockTransport(
        lambda request: httpx.Response(422, json=payload)
    ))
    with pytest.raises(InvalidReconstructionOutputError):
        adapter.reconstruct(inputs(), FurnitureType.CHAIR, dimensions())


def test_reconstruction_timeout_does_not_expose_transport_details():
    def timeout(request):
        raise httpx.ReadTimeout("private transport detail", request=request)
    adapter = HttpFurnitureReconstructor("http://worker", 30, transport=httpx.MockTransport(timeout))
    with pytest.raises(ReconstructionProviderUnavailableError, match="timed out; no new drawing was saved"):
        adapter.reconstruct(inputs(), FurnitureType.CHAIR, dimensions())


def test_worker_rejection_detail_is_bounded():
    adapter = HttpFurnitureReconstructor("http://worker", 30, transport=httpx.MockTransport(
        lambda request: httpx.Response(422, json={"detail": "x" * 1000})
    ))
    with pytest.raises(ReconstructionInputRejectedError) as caught:
        adapter.reconstruct(inputs(), FurnitureType.CHAIR, dimensions())
    assert len(str(caught.value)) == 300
