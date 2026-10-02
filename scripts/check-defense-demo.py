"""Read-only local defense check: finalized 2D -> 3D -> quantities -> quote.

Run with the existing WUE virtual environment. Only business API GET requests
are issued. This verifies data consistency, not photo accuracy or build safety.
"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, localcontext
from uuid import UUID

import httpx


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def decimal(value) -> Decimal:
    return Decimal(str(value))


def index_unique(items: list[dict], key: str) -> dict[str, dict]:
    indexed = {item[key]: item for item in items}
    require(len(indexed) == len(items), f"Duplicate {key} in response")
    return indexed


def check_geometry(plan: dict, geometry: dict) -> None:
    require(plan["status"] == "finalized", "Selected source plan is not finalized")
    require(geometry["unit"] == "mm", "Unexpected 3D unit")
    for key, plan_key in (("plan_id", "id"), ("furniture_id", "furniture_id"),
                          ("revision", "revision"), ("furniture_type", "furniture_type")):
        require(geometry[key] == plan[plan_key], f"3D {key} differs from source plan")
    source = index_unique(plan["components"], "id")
    derived = index_unique(geometry["components"], "source_component_id")
    require(source.keys() == derived.keys(), "3D source component IDs differ")
    for component_id, part in source.items():
        item = derived[component_id]
        for key in ("component_name", "component_type", "geometry_kind", "quantity", "sort_order"):
            require(item[key] == part[key], f"3D {key} differs for {part['component_name']}")
        require(item["profile_points"] == part["profile_points"], "3D profile differs from 2D")
        depth = part["depth"] if part["depth"] is not None else part["thickness"]
        require(depth is not None, "Source part has no depth or thickness")
        sizes = {"width": part["width"], "height": part["height"], "depth": depth}
        for dimension, axis in zip(("width", "height", "depth"), ("x", "y", "z"), strict=True):
            require(decimal(item["dimensions"][dimension]) == decimal(sizes[dimension]), "3D size differs")
            require(decimal(item["min_corner"][axis]) == decimal(part[axis]), "3D placement differs")
            expected_center = decimal(part[axis]) + decimal(sizes[dimension]) / 2
            require(decimal(item["center"][axis]) == expected_center, "3D center differs")
        for axis, key in (("x", "rotation_x"), ("y", "rotation_y"), ("z", "rotation_z")):
            require(decimal(item["rotation"][axis]) == decimal(part[key]), "3D rotation differs")


def part_volume(part: dict) -> Decimal:
    # Match the quantity calculator's Decimal context, independently of its code.
    with localcontext() as context:
        context.prec = 28
        points = part["profile_points"]
        if points is None:
            area = decimal(part["dimensions"]["width"]) * decimal(part["dimensions"]["height"])
        else:
            require(len(points) >= 3, "Profile has fewer than three points")
            area = abs(sum(
                decimal(point["u"]) * decimal(points[(i + 1) % len(points)]["v"])
                - decimal(points[(i + 1) % len(points)]["u"]) * decimal(point["v"])
                for i, point in enumerate(points)
            )) / 2
        return area * decimal(part["dimensions"]["depth"]) * part["quantity"]


def check_quantities(plan: dict, geometry: dict, materials: dict, hardware: dict, labor: dict) -> None:
    for response in (materials, hardware, labor):
        require(response["plan_id"] == plan["id"] and response["revision"] == plan["revision"],
                "Quantity response uses a different revision")
    derived = index_unique(geometry["components"], "source_component_id")
    rows = index_unique(materials["components"], "source_component_id")
    require(derived.keys() == rows.keys(), "Material source component IDs differ")
    with localcontext() as context:
        context.prec = 28
        total = Decimal(0)
        for component_id, part in derived.items():
            volume = part_volume(part)
            require(rows[component_id]["quantity"] == part["quantity"], "Material part count differs")
            require(decimal(rows[component_id]["total_volume_mm3"]) == volume, "Material volume differs")
            total += volume
        require(decimal(materials["total_volume_mm3"]) == total, "Total material volume differs")
    require(hardware["total_quantity"] == sum(row["screw_quantity"] for row in hardware["connections"]),
            "Hardware quantity does not sum")
    for row in hardware["connections"]:
        require(row["screw_quantity"] == row["connection_count"] * row["screws_per_connection"],
                "Hardware connection calculation differs")
    require(decimal(labor["labor_hours"]) == sum(decimal(row["labor_hours"]) for row in labor["rules"]),
            "Labor hours do not sum")
    for row in labor["rules"]:
        require(decimal(row["labor_hours"]) == row["unit_count"] * decimal(row["hours_per_unit"]),
                "Labor rule calculation differs")


def check_quote(plan: dict, materials: dict, hardware: dict, labor: dict, quote: dict) -> None:
    require(quote["plan_id"] == plan["id"] and quote["plan_revision"] == plan["revision"],
            "Quotation does not reference the selected finalized revision")
    require(quote["furniture_id"] == plan["furniture_id"], "Quotation furniture differs")
    divisors = {"mm3": "1", "cm3": "1000", "m3": "1000000000", "board_ft": "2359737.216"}
    require(quote["wood_price_unit"] in divisors, "Unsupported wood price unit")
    with localcontext() as context:
        context.prec = 40
        expected_wood = decimal(materials["total_volume_mm3"]) / decimal(divisors[quote["wood_price_unit"]])
        require(decimal(quote["wood_quantity"]) == expected_wood, "Quote wood quantity differs from BOM")
        require(quote["hardware_quantity"] == hardware["total_quantity"], "Quote hardware quantity differs")
        require(decimal(quote["labor_hours"]) == decimal(labor["labor_hours"]), "Quote labor hours differ")
        for cost, quantity, price in (
            ("wood_material_cost", "wood_quantity", "wood_price_per_unit"),
            ("hardware_cost", "hardware_quantity", "hardware_price_per_piece"),
            ("labor_cost", "labor_hours", "labor_rate_per_hour"),
        ):
            require(decimal(quote[cost]) == decimal(quote[quantity]) * decimal(quote[price]),
                    f"Quotation {cost} differs from its saved prices")
        expected_total = sum(decimal(quote[key]) for key in ("wood_material_cost", "hardware_cost", "labor_cost"))
        require(decimal(quote["total_cost"]) == expected_total, "Quotation total does not sum")


def latest_prices_match(cost: dict, quote: dict) -> bool:
    # Admin edits may change a price's value without changing its ID. The saved
    # quotation remains historical; a different current estimate is not a bug.
    return all(cost[group][key] == quote[quote_key] for group, key, quote_key in (
        ("material", "price_id", "wood_price_id"), ("hardware", "price_id", "hardware_price_id"),
        ("labor", "price_id", "labor_rate_price_id"), ("material", "price_unit", "wood_price_unit"),
    )) and all(decimal(cost[group][key]) == decimal(quote[quote_key]) for group, key, quote_key in (
        ("material", "price_per_unit", "wood_price_per_unit"),
        ("hardware", "price_per_piece", "hardware_price_per_piece"),
        ("labor", "rate_per_hour", "labor_rate_per_hour"),
    ))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_id", type=UUID)
    parser.add_argument("quotation_id", type=UUID)
    parser.add_argument("--draft-plan-id", type=UUID)
    args = parser.parse_args()
    with httpx.Client(base_url="http://127.0.0.1:8011/api/v1", timeout=30) as client:
        def read(path, params=None):
            response = client.get(path, params=params)
            response.raise_for_status()
            return response.json()

        prefix = f"/plans/{args.plan_id}"
        plan = read(prefix)
        quote_path = f"/quotations/{args.quotation_id}"
        quote = read(quote_path)
        geometry = read(prefix + "/geometry-3d")
        materials = read(prefix + "/material-quantity")
        hardware = read(prefix + "/hardware-quantity")
        labor = read(prefix + "/labor-quantity")
        check_geometry(plan, geometry)
        check_quantities(plan, geometry, materials, hardware, labor)
        check_quote(plan, materials, hardware, labor, quote)
        selection = {"material_id": quote["wood_material_id"],
                     "hardware_material_id": quote["hardware_material_id"],
                     "labor_rate_id": quote["labor_rate_id"]}
        cost = read(prefix + "/complete-cost", selection)
        with localcontext() as context:
            context.prec = 40
            require(decimal(cost["total_cost"]) == sum(decimal(cost[key]["total_cost"])
                    for key in ("material", "hardware", "labor")), "Live cost total does not sum")
        latest_matches = latest_prices_match(cost, quote)
        if latest_matches:
            require(decimal(cost["total_cost"]) == decimal(quote["total_cost"]),
                    "Unchanged prices yield a different live/saved total")
        blocked = []
        if args.draft_plan_id:
            draft_path = f"/plans/{args.draft_plan_id}"
            draft_before = read(draft_path)
            require(draft_before["status"] == "draft", "Requested guard-check plan is not a draft")
            for suffix in ("geometry-3d", "material-quantity", "hardware-quantity", "labor-quantity", "complete-cost"):
                response = client.get(draft_path + "/" + suffix,
                                      params=selection if suffix == "complete-cost" else None)
                require(response.status_code == 409, f"Draft {suffix} did not return 409")
                blocked.append(suffix)
            require(read(draft_path) == draft_before, "Draft changed during check; inspect concurrent edits")
        require(read(prefix) == plan and read(quote_path) == quote,
                "Saved source or quote changed during check; inspect concurrent edits")
        print(json.dumps({
            "check_passed": True, "business_api_methods_used": ["GET"],
            "plan_id": str(args.plan_id), "quotation_id": str(args.quotation_id),
            "source_revision": plan["revision"], "component_count": len(plan["components"]),
            "wood_quantity": quote["wood_quantity"], "wood_price_unit": quote["wood_price_unit"],
            "hardware_quantity": quote["hardware_quantity"], "labor_hours": quote["labor_hours"],
            "saved_total_cost": quote["total_cost"], "latest_prices_match_saved_quote": latest_matches,
            "draft_routes_blocked": blocked, "checked_saved_records_unchanged": True,
            "physical_accuracy_verified": False, "manufacturing_safety_verified": False,
            "limitations": ["Net volume excludes purchasing waste and nesting",
                            "Hardware and labor use WUE v1 assumptions, not verified joinery/time",
                            "Demo prices and approximate dimensions require explicit disclosure"],
        }, indent=2))


def cli() -> int:
    try:
        main()
    except httpx.ConnectError:
        print("CHECK NOT COMPLETED: WUE API is unavailable. Start scripts/start-wue.ps1 "
              "and retry. This checker issued no write requests.", file=sys.stderr)
        return 1
    except httpx.TimeoutException:
        print("CHECK NOT COMPLETED: WUE API did not respond in time. Check service readiness "
              "and retry. This checker issued no write requests.", file=sys.stderr)
        return 1
    except httpx.HTTPStatusError as error:
        print(f"CHECK NOT COMPLETED: WUE API returned HTTP {error.response.status_code}. "
              "Check the selected plan/quotation IDs and service readiness. "
              "This checker issued no write requests.", file=sys.stderr)
        return 1
    except ValueError as error:
        print(f"CHECK FAILED: {error}. This checker issued no write requests.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
