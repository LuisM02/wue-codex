"""Read-only recognition probe; never persists a classification or changes plans.

Run using the repository's installed Python environment. A successful response
is an accepted structural hypothesis, not an open-world accuracy benchmark.
"""

import argparse
import hashlib
import json

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("furniture_id")
    args = parser.parse_args()
    api = "http://127.0.0.1:8011/api/v1"
    prefix = f"/furniture/{args.furniture_id}"
    with httpx.Client(timeout=600) as client:
        def read(path):
            response = client.get(api + path)
            if response.status_code == 404 and path.endswith("/classification"):
                return None
            response.raise_for_status()
            return response.json()

        furniture = read(prefix)
        plans = read(prefix + "/plans")
        classification = read(prefix + "/classification")
        images = read(prefix + "/images")
        files, manifest = {}, []
        for image in images:
            view = image["view"]
            response = client.get(api + prefix + f"/images/{view}/content")
            response.raise_for_status()
            checksum = hashlib.sha256(response.content).hexdigest()
            if checksum != image["checksum_sha256"]:
                raise RuntimeError(f"Saved {view} image integrity check failed")
            files[view] = (image["original_filename"], response.content, image["content_type"])
            manifest.append({"view": view, "checksum_sha256": checksum})
        response = client.post("http://127.0.0.1:8010/v1/classify", files=files,
                               data={"image_manifest": json.dumps(manifest)})
        if response.status_code not in (200, 422):
            response.raise_for_status()
        if (read(prefix) != furniture or read(prefix + "/plans") != plans
                or read(prefix + "/classification") != classification
                or read(prefix + "/images") != images):
            raise RuntimeError("Saved state changed; check for concurrent edits")
        print(json.dumps({"furniture": furniture["name"], "status": response.status_code,
                          "result": response.json(), "saved_state_unchanged": True,
                          "accuracy_verified": False}, indent=2))


if __name__ == "__main__":
    main()
