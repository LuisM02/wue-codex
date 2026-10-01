"""Analyze saved photos without writing reconstruction, plans, or quotations.

Run with the existing repository virtual environment. This checks inference,
not measured accuracy; the selected furniture's saved dimensions are reused.
"""

import argparse
import hashlib
import json

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("furniture_id")
    args = parser.parse_args()
    api_url = "http://127.0.0.1:8011/api/v1"
    worker_url = "http://127.0.0.1:8010"
    with httpx.Client(timeout=600) as client:
        def read(path: str):
            response = client.get(f"{api_url}{path}")
            response.raise_for_status()
            return response.json()

        prefix = f"/furniture/{args.furniture_id}"
        furniture = read(prefix)
        dimensions = read(f"{prefix}/dimensions")
        images = read(f"{prefix}/images")
        plans_before = read(f"{prefix}/plans")
        files = {}
        manifest = []
        for image in images:
            view = image["view"]
            response = client.get(f"{api_url}{prefix}/images/{view}/content")
            response.raise_for_status()
            checksum = hashlib.sha256(response.content).hexdigest()
            if checksum != image["checksum_sha256"]:
                raise RuntimeError(f"Saved {view} photo does not match its recorded checksum")
            files[view] = (image["original_filename"], response.content, image["content_type"])
            manifest.append({"view": view, "checksum_sha256": checksum})
        response = client.post(
            f"{worker_url}/v1/reconstruct",
            files=files,
            data={
                "furniture_type": furniture["furniture_type"],
                "width_mm": dimensions["width_mm"],
                "height_mm": dimensions["height_mm"],
                "depth_mm": dimensions["depth_mm"],
                "image_manifest": json.dumps(manifest),
            },
        )
        response.raise_for_status()
        proposal = response.json()
        if read(f"{prefix}/plans") != plans_before:
            raise RuntimeError("Saved plans changed during the probe; check for concurrent editing")
        print(json.dumps({
            "furniture": furniture["name"],
            "provider": proposal["provider_name"],
            "proposed_parts": [part["component_name"] for part in proposal["parts"]],
            "part_sizes_mm": [{key: part[key] for key in ("component_name", "width", "height", "depth")} for part in proposal["parts"]],
            "warnings": proposal["warnings"],
            "saved_plans_unchanged": True,
            "accuracy_verified": False,
        }, indent=2))


if __name__ == "__main__":
    main()
