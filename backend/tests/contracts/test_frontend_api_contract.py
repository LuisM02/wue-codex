"""Verify that every route used by the frontend exists in FastAPI OpenAPI."""

import json
from pathlib import Path

from app.main import app

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = REPOSITORY_ROOT / "contracts" / "frontend-api.json"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def load_operations() -> list[tuple[str, str]]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["version"] == 1
    base_path = contract["base_path"]
    operations = [
        (item["method"].upper(), item["path"])
        for item in contract["operations"]
    ]
    assert all(path.startswith(f"{base_path}/") for _, path in operations)
    assert len(operations) == len(set(operations)), "Contract operations must be unique"
    return operations


def test_every_frontend_operation_exists_in_openapi() -> None:
    openapi_paths = app.openapi()["paths"]
    available = {
        (method.upper(), path)
        for path, path_item in openapi_paths.items()
        for method in path_item
        if method in HTTP_METHODS
    }

    missing = set(load_operations()) - available

    assert not missing, f"Frontend operations missing from FastAPI: {sorted(missing)}"
