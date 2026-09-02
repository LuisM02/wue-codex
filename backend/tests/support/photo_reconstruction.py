"""Explicit fake reconstruction provider used only by existing plan tests."""

from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.api.dependencies import get_furniture_reconstructor
from app.core.enums import FurnitureImageView
from app.main import app
from app.models.furniture_reconstruction import FurnitureReconstruction
from app.models.furniture_reconstruction_part import FurnitureReconstructionPart
from app.schemas.photo_reconstruction import ReconstructionPartProposal
from app.services.photo_reconstruction import ReconstructionPrediction
from app.services.plan_geometry import generate_default_components


class TemplateTestReconstructor:
    """Preserve historical test fixtures without enabling production templates."""

    def reconstruct(self, images, furniture_type, dimensions):
        seeds = generate_default_components(
            furniture_type,
            width_mm=dimensions.width_mm,
            height_mm=dimensions.height_mm,
            depth_mm=dimensions.depth_mm,
        )
        return ReconstructionPrediction(
            provider_name="explicit-test-fixture",
            provider_version="1",
            confidence="1",
            warnings=("Synthetic geometry used by an automated test only",),
            parts=tuple(
                ReconstructionPartProposal(
                    component_name=seed.component_name,
                    component_type=seed.component_type,
                    width=seed.width,
                    height=seed.height,
                    depth=seed.depth or seed.thickness,
                    x=seed.x,
                    y=seed.y,
                    z=seed.z,
                    rotation_y=seed.rotation,
                    quantity=seed.quantity,
                    sort_order=seed.sort_order,
                    confidence="1",
                    source_views=list(FurnitureImageView),
                )
                for seed in seeds
            ),
        )


def _png_bytes(color: tuple[int, int, int]) -> bytes:
    output = BytesIO()
    Image.new("RGB", (8, 6), color=color).save(output, format="PNG")
    return output.getvalue()


def prepare_test_reconstruction(client: TestClient, furniture_id: str) -> dict:
    """Upload the required views and persist an explicitly configured fake result."""
    for index, view in enumerate(FurnitureImageView):
        data = _png_bytes((80 + index * 10, 60, 40))
        response = client.post(
            f"/api/v1/furniture/{furniture_id}/images/{view.value}",
            files={"file": (f"{view.value}.png", data, "image/png")},
            data={"source": "upload"},
        )
        assert response.status_code == 201
    app.dependency_overrides[get_furniture_reconstructor] = TemplateTestReconstructor
    response = client.post(f"/api/v1/furniture/{furniture_id}/reconstruction")
    assert response.status_code == 200, response.text
    return response.json()


def seed_test_reconstruction(session, furniture, dimensions) -> FurnitureReconstruction:
    """Persist the same explicit test geometry without crossing the HTTP boundary."""
    reconstruction = FurnitureReconstruction(
        furniture_id=furniture.id,
        input_signature="0" * 64,
        furniture_type=furniture.furniture_type,
        provider_name="explicit-test-fixture",
        provider_version="1",
        confidence="1",
        warnings=["Synthetic geometry used by an automated test only"],
    )
    session.add(reconstruction)
    session.flush()
    for seed in generate_default_components(
        furniture.furniture_type,
        width_mm=dimensions.width_mm,
        height_mm=dimensions.height_mm,
        depth_mm=dimensions.depth_mm,
    ):
        reconstruction.parts.append(
            FurnitureReconstructionPart(
                component_name=seed.component_name,
                component_type=seed.component_type,
                geometry_kind="box",
                profile_points=None,
                width=seed.width,
                height=seed.height,
                depth=seed.depth or seed.thickness,
                x=seed.x,
                y=seed.y,
                z=seed.z,
                rotation_x="0",
                rotation_y=seed.rotation,
                rotation_z="0",
                quantity=seed.quantity,
                sort_order=seed.sort_order,
                confidence="1",
                source_views=[view.value for view in FurnitureImageView],
            )
        )
    session.commit()
    return reconstruction
