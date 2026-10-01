"""Probe five photos; optionally import an explicitly named separate test draft."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import httpx


def save_test_copy(client, files, dimensions, name):
    api_url = "http://127.0.0.1:8011/api/v1"

    def request(method, path, **kwargs):
        response = client.request(method, f"{api_url}{path}", **kwargs)
        response.raise_for_status()
        return response.json()

    projects = request("GET", "/projects")
    project = next((item for item in projects if item["name"] == "Photo reconstruction tests"), None)
    if project is None:
        project = request("POST", "/projects", json={
            "name": "Photo reconstruction tests",
            "description": "Separate test drafts with user-approved approximate dimensions; not accuracy benchmarks.",
        })
    items = request("GET", f"/projects/{project['id']}/furniture")
    if any(item["name"] == name for item in items):
        raise RuntimeError("A test copy with that name already exists; no existing furniture was changed")
    furniture = request("POST", f"/projects/{project['id']}/furniture", json={"name": name})
    prefix = f"/furniture/{furniture['id']}"
    print(f"Created test furniture {furniture['id']} in project {project['id']}", file=sys.stderr)
    for view, file in files.items():
        request("POST", f"{prefix}/images/{view}", files={"file": file}, data={"source": "upload"})
    classification = request("POST", f"{prefix}/classification")
    request("PUT", f"{prefix}/dimensions", json={
        "width": dimensions[0], "height": dimensions[1], "depth": dimensions[2],
        "unit": "mm", "source": "manual",
    })
    analysis = request("POST", f"{prefix}/reconstruction")
    plan = request("POST", f"{prefix}/plans")
    return {
        "project_id": project["id"], "furniture_id": furniture["id"], "plan_id": plan["id"],
        "plan_status": plan["status"], "parts_reviewed_at": plan["parts_reviewed_at"],
        "classification": classification, "supplied_approximate_dimensions_mm": dimensions,
        "proposed_parts": [{key: part[key] for key in ("component_name", "width", "height", "depth")} for part in analysis["parts"]],
        "warnings": analysis["warnings"], "records_saved": True, "accuracy_verified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    views = ("front", "back", "left", "right", "top")
    for view in views:
        parser.add_argument(f"--{view}", type=Path, required=True)
    for axis in ("width", "height", "depth"):
        parser.add_argument(f"--{axis}", type=float)
    parser.add_argument("--save-test-copy", metavar="NAME", help="Explicit opt-in to import a separate unreviewed draft through the local API")
    args = parser.parse_args()
    dimensions = (args.width, args.height, args.depth)
    if any(value is not None for value in dimensions) and not all(
        value is not None and value > 0 for value in dimensions
    ):
        parser.error("Provide all three positive dimensions in millimeters, or omit all three for classification only")
    if args.save_test_copy and not all(value is not None for value in dimensions):
        parser.error("Saving a separate test copy requires supplied dimensions")
    files = {}
    manifest = []
    for view in views:
        path = getattr(args, view)
        data = path.read_bytes()
        mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(path.suffix.lower())
        if mime is None:
            parser.error(f"Unsupported file type for {view}")
        files[view] = (path.name, data, mime)
        manifest.append({"view": view, "checksum_sha256": hashlib.sha256(data).hexdigest()})
    with httpx.Client(timeout=600) as client:
        if args.save_test_copy:
            print(json.dumps(save_test_copy(client, files, dimensions, args.save_test_copy), indent=2))
            return
        classification = client.post(
            "http://127.0.0.1:8010/v1/classify", files=files,
            data={"image_manifest": json.dumps(manifest)},
        )
        classification.raise_for_status()
        result = {"classification": classification.json(), "records_saved": False, "accuracy_verified": False}
        if all(value is not None for value in dimensions):
            response = client.post(
                "http://127.0.0.1:8010/v1/reconstruct", files=files,
                data={
                    "furniture_type": result["classification"]["furniture_type"],
                    "width_mm": str(args.width), "height_mm": str(args.height), "depth_mm": str(args.depth),
                    "image_manifest": json.dumps(manifest),
                },
            )
            response.raise_for_status()
            proposal = response.json()
            result["supplied_dimensions_mm"] = dimensions
            result["provider"] = proposal["provider_name"]
            result["parts"] = proposal["parts"]
            result["warnings"] = proposal["warnings"]
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
