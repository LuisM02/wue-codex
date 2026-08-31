"""Real PostgreSQL API tests for manual-first overall dimensions."""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.dimensions import (
    DimensionsRequiredError,
    lock_dimensions_for_plan,
)

pytestmark = pytest.mark.integration


def create_furniture(client: TestClient) -> str:
    project = client.post("/api/v1/projects", json={"name": "Dimensions"})
    furniture = client.post(
        f"/api/v1/projects/{project.json()['id']}/furniture",
        json={"name": "Measured item", "furniture_type": "chair"},
    )
    return furniture.json()["id"]


@pytest.mark.parametrize(
    ("unit", "values", "expected_mm"),
    [
        ("mm", ("600", "900", "500"), ("600.0000", "900.0000", "500.0000")),
        ("cm", ("60", "90", "50"), ("600.0000", "900.0000", "500.0000")),
        ("m", ("0.6", "0.9", "0.5"), ("600.0000", "900.0000", "500.0000")),
        (
            "in",
            ("23.622", "35.433", "19.685"),
            ("599.9988", "899.9982", "499.9990"),
        ),
    ],
)
def test_creates_and_reads_canonical_dimensions_for_each_unit(
    db_client: TestClient,
    unit: str,
    values: tuple[str, str, str],
    expected_mm: tuple[str, str, str],
) -> None:
    furniture_id = create_furniture(db_client)
    width, height, depth = values

    create_response = db_client.put(
        f"/api/v1/furniture/{furniture_id}/dimensions",
        json={"width": width, "height": height, "depth": depth, "unit": unit},
    )

    assert create_response.status_code == 201
    result = create_response.json()
    assert (result["width_mm"], result["height_mm"], result["depth_mm"]) == (
        expected_mm
    )
    assert result["unit"] == unit
    assert result["source"] == "manual"
    assert result["is_locked"] is False
    assert result["locked_at"] is None

    read_response = db_client.get(
        f"/api/v1/furniture/{furniture_id}/dimensions"
    )
    assert read_response.status_code == 200
    assert read_response.json() == result


def test_updates_unlocked_dimensions_and_allows_manual_to_replace_ai(
    db_client: TestClient,
) -> None:
    furniture_id = create_furniture(db_client)
    url = f"/api/v1/furniture/{furniture_id}/dimensions"
    ai_response = db_client.put(
        url,
        json={
            "width": "70",
            "height": "100",
            "depth": "60",
            "unit": "cm",
            "source": "ai_estimate",
        },
    )
    assert ai_response.status_code == 201

    manual_response = db_client.put(
        url,
        json={"width": "700", "height": "1000", "depth": "600", "unit": "mm"},
    )

    assert manual_response.status_code == 200
    assert manual_response.json()["id"] == ai_response.json()["id"]
    assert manual_response.json()["source"] == "manual"


def test_ai_estimate_cannot_overwrite_trusted_manual_dimensions(
    db_client: TestClient,
) -> None:
    furniture_id = create_furniture(db_client)
    url = f"/api/v1/furniture/{furniture_id}/dimensions"
    assert db_client.put(
        url,
        json={"width": 1, "height": 2, "depth": 3, "unit": "m"},
    ).status_code == 201

    response = db_client.put(
        url,
        json={
            "width": 2,
            "height": 3,
            "depth": 4,
            "unit": "m",
            "source": "ai_estimate",
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "AI-estimated dimensions cannot replace trusted manual dimensions"
    }


def test_unlocked_dimensions_can_be_deleted(db_client: TestClient) -> None:
    furniture_id = create_furniture(db_client)
    url = f"/api/v1/furniture/{furniture_id}/dimensions"
    db_client.put(
        url,
        json={"width": 600, "height": 900, "depth": 500, "unit": "mm"},
    )

    response = db_client.delete(url)

    assert response.status_code == 204
    assert db_client.get(url).status_code == 404


def test_2d_plan_lock_is_permanent_for_dimension_mutations(
    db_client: TestClient,
    db_session: Session,
) -> None:
    furniture_id = create_furniture(db_client)
    url = f"/api/v1/furniture/{furniture_id}/dimensions"
    db_client.put(
        url,
        json={"width": 600, "height": 900, "depth": 500, "unit": "mm"},
    )
    first_lock = lock_dimensions_for_plan(db_session, UUID(furniture_id))
    first_locked_at = first_lock.locked_at
    second_lock = lock_dimensions_for_plan(db_session, UUID(furniture_id))
    db_session.commit()

    assert second_lock.locked_at == first_locked_at
    locked = db_client.get(url).json()
    assert locked["is_locked"] is True
    assert locked["locked_at"] is not None

    update = db_client.put(
        url,
        json={"width": 601, "height": 901, "depth": 501, "unit": "mm"},
    )
    delete = db_client.delete(url)
    expected = {
        "detail": "Overall dimensions are locked because a 2D plan has been generated"
    }
    assert update.status_code == 409
    assert update.json() == expected
    assert delete.status_code == 409
    assert delete.json() == expected


def test_lock_requires_dimensions(db_session: Session, db_client: TestClient) -> None:
    furniture_id = create_furniture(db_client)

    with pytest.raises(DimensionsRequiredError, match="required"):
        lock_dimensions_for_plan(db_session, UUID(furniture_id))


def test_missing_resources_validation_and_canonical_overflow(
    db_client: TestClient,
) -> None:
    missing_id = uuid4()
    missing_url = f"/api/v1/furniture/{missing_id}/dimensions"
    payload = {"width": 1, "height": 1, "depth": 1, "unit": "mm"}
    assert db_client.get(missing_url).status_code == 404
    assert db_client.put(missing_url, json=payload).status_code == 404

    furniture_id = create_furniture(db_client)
    url = f"/api/v1/furniture/{furniture_id}/dimensions"
    assert db_client.get(url).status_code == 404
    assert db_client.put(url, json={**payload, "width": 0}).status_code == 422
    overflow = db_client.put(
        url,
        json={"width": "10000000", "height": 1, "depth": 1, "unit": "m"},
    )
    assert overflow.status_code == 422
    assert "Converted dimension" in overflow.json()["detail"]
