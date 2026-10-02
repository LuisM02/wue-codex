"""Controlled consistency failures; these tests never contact a live service."""
import copy
import importlib.util
import json
from pathlib import Path

import httpx
import pytest

spec = importlib.util.spec_from_file_location(
    "defense_checker", Path(__file__).resolve().parents[1] / "check-defense-demo.py",
)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)

PLAN = "00000000-0000-4000-8000-000000000001"
QUOTE = "00000000-0000-4000-8000-000000000002"
DRAFT = "00000000-0000-4000-8000-000000000003"


@pytest.fixture
def records():
    component = {
        "id": "part", "component_name": "tabletop", "component_type": "panel",
        "geometry_kind": "box", "quantity": 2, "sort_order": 0,
        "width": "4", "height": "3", "depth": "2", "thickness": None,
        "x": "0", "y": "0", "z": "0", "profile_points": None,
        "rotation_x": "0", "rotation_y": "0", "rotation_z": "0",
    }
    plan = {"id": PLAN, "furniture_id": "furniture", "revision": 1,
            "furniture_type": "dining_table", "status": "finalized", "components": [component]}
    geometry = {"plan_id": PLAN, "furniture_id": "furniture", "revision": 1,
                "furniture_type": "dining_table", "unit": "mm", "components": [{
                    "source_component_id": "part", "component_name": "tabletop", "component_type": "panel",
                    "geometry_kind": "box", "quantity": 2, "sort_order": 0, "profile_points": None,
                    "dimensions": {"width": "4", "height": "3", "depth": "2"},
                    "min_corner": {"x": "0", "y": "0", "z": "0"},
                    "center": {"x": "2", "y": "1.5", "z": "1"},
                    "rotation": {"x": "0", "y": "0", "z": "0"},
                }]}
    materials = {"plan_id": PLAN, "revision": 1, "total_volume_mm3": "48",
                 "components": [{"source_component_id": "part", "quantity": 2, "total_volume_mm3": "48"}]}
    hardware = {"plan_id": PLAN, "revision": 1, "total_quantity": 8,
                "connections": [{"connection_count": 4, "screws_per_connection": 2, "screw_quantity": 8}]}
    labor = {"plan_id": PLAN, "revision": 1, "labor_hours": "3.20",
             "rules": [{"unit_count": 4, "hours_per_unit": ".80", "labor_hours": "3.20"}]}
    quote = {"id": QUOTE, "plan_id": PLAN, "plan_revision": 1, "furniture_id": "furniture",
             "wood_price_unit": "mm3", "wood_quantity": "48", "wood_price_per_unit": "1",
             "wood_material_cost": "48", "hardware_quantity": 8, "hardware_price_per_piece": "2",
             "hardware_cost": "16", "labor_hours": "3.20", "labor_rate_per_hour": "150",
             "labor_cost": "480", "total_cost": "544", "wood_material_id": "wood",
             "hardware_material_id": "screw", "labor_rate_id": "rate",
             "wood_price_id": "wood-price", "hardware_price_id": "screw-price", "labor_rate_price_id": "rate-price"}
    return plan, geometry, materials, hardware, labor, quote


def test_consistent_box_chain(records):
    plan, geometry, materials, hardware, labor, quote = records
    checker.check_geometry(plan, geometry)
    checker.check_quantities(plan, geometry, materials, hardware, labor)
    checker.check_quote(plan, materials, hardware, labor, quote)


def test_polygon_uses_area_not_bounding_rectangle(records):
    plan, geometry, materials, hardware, labor, _ = records
    points = [{"u": "0", "v": "0"}, {"u": "4", "v": "0"}, {"u": "0", "v": "3"}]
    for part in (plan["components"][0], geometry["components"][0]):
        part["profile_points"] = points
        part["geometry_kind"] = "extruded_profile"
    materials["components"][0]["total_volume_mm3"] = "24"
    materials["total_volume_mm3"] = "24"
    checker.check_geometry(plan, geometry)
    checker.check_quantities(plan, geometry, materials, hardware, labor)
    assert checker.part_volume(geometry["components"][0]) == 24


@pytest.mark.parametrize("field,key,value,message", [
    ("dimensions", "width", "99", "3D size differs"),
    ("min_corner", "x", "99", "3D placement differs"),
    ("center", "x", "99", "3D center differs"),
    ("rotation", "x", "15", "3D rotation differs"),
])
def test_geometry_drift_is_detected(records, field, key, value, message):
    plan, geometry, *_ = records
    geometry["components"][0][field][key] = value
    with pytest.raises(ValueError, match=message):
        checker.check_geometry(plan, geometry)


def test_duplicate_source_ids_are_not_silently_ignored(records):
    plan, geometry, *_ = records
    geometry["components"].append(copy.deepcopy(geometry["components"][0]))
    with pytest.raises(ValueError, match="Duplicate source_component_id"):
        checker.check_geometry(plan, geometry)


def test_wrong_material_volume_is_detected(records):
    plan, geometry, materials, hardware, labor, _ = records
    materials["components"][0]["total_volume_mm3"] = "99"
    with pytest.raises(ValueError, match="Material volume differs"):
        checker.check_quantities(plan, geometry, materials, hardware, labor)


def test_wrong_saved_quote_total_is_detected(records):
    plan, _, materials, hardware, labor, quote = records
    quote["total_cost"] = "999"
    with pytest.raises(ValueError, match="Quotation total does not sum"):
        checker.check_quote(plan, materials, hardware, labor, quote)


@pytest.mark.parametrize("guard_status", [409, 200])
def test_main_uses_only_get_and_checks_draft_guards(records, monkeypatch, capsys, guard_status):
    plan, geometry, materials, hardware, labor, quote = records
    draft = {"id": DRAFT, "status": "draft", "parts_reviewed_at": None}
    responses = {
        f"/api/v1/plans/{PLAN}": plan,
        f"/api/v1/quotations/{QUOTE}": quote,
        f"/api/v1/plans/{PLAN}/geometry-3d": geometry,
        f"/api/v1/plans/{PLAN}/material-quantity": materials,
        f"/api/v1/plans/{PLAN}/hardware-quantity": hardware,
        f"/api/v1/plans/{PLAN}/labor-quantity": labor,
        f"/api/v1/plans/{PLAN}/complete-cost": {
            "material": {"price_id": "wood-price", "price_unit": "mm3", "price_per_unit": "1", "total_cost": "48"},
            "hardware": {"price_id": "screw-price", "price_per_piece": "2", "total_cost": "16"},
            "labor": {"price_id": "rate-price", "rate_per_hour": "150", "total_cost": "480"}, "total_cost": "544",
        },
        f"/api/v1/plans/{DRAFT}": draft,
    }
    methods = []

    def respond(request):
        methods.append(request.method)
        if request.url.path.startswith(f"/api/v1/plans/{DRAFT}/"):
            return httpx.Response(guard_status, json={"detail": "Finalized plan required"})
        return httpx.Response(200, json=responses[request.url.path])

    real_client = httpx.Client
    monkeypatch.setattr(checker.httpx, "Client", lambda **kwargs: real_client(
        **kwargs, transport=httpx.MockTransport(respond),
    ))
    monkeypatch.setattr("sys.argv", ["check-defense-demo.py", PLAN, QUOTE, "--draft-plan-id", DRAFT])
    if guard_status == 409:
        checker.main()
        report = json.loads(capsys.readouterr().out)
        assert report["check_passed"] and len(report["draft_routes_blocked"]) == 5
    else:
        with pytest.raises(ValueError, match="Draft geometry-3d did not return 409"):
            checker.main()
    assert methods and set(methods) == {"GET"}


def test_edited_live_price_does_not_invalidate_historical_quote(records):
    quote = records[-1]
    current = {
        "material": {"price_id": "wood-price", "price_unit": "mm3", "price_per_unit": "1"},
        "hardware": {"price_id": "screw-price", "price_per_piece": "2"},
        "labor": {"price_id": "rate-price", "rate_per_hour": "150"},
    }
    assert checker.latest_prices_match(current, quote)
    current["material"]["price_per_unit"] = "5"
    assert not checker.latest_prices_match(current, quote)


@pytest.mark.parametrize("error,message", [
    (httpx.ConnectError("internal connection details"), "WUE API is unavailable"),
    (httpx.ReadTimeout("internal timeout details"), "did not respond in time"),
    (httpx.HTTPStatusError("internal HTTP details", request=httpx.Request("GET", "http://localhost"),
                          response=httpx.Response(404)), "HTTP 404"),
    (ValueError("3D size differs"), "3D size differs"),
])
def test_cli_reports_failures_without_tracebacks(monkeypatch, capsys, error, message):
    def fail():
        raise error
    monkeypatch.setattr(checker, "main", fail)
    assert checker.cli() == 1
    output = capsys.readouterr()
    assert not output.out
    assert message in output.err and "no write requests" in output.err
    assert "Traceback" not in output.err and "internal" not in output.err


def test_cli_success_returns_zero(monkeypatch):
    monkeypatch.setattr(checker, "main", lambda: None)
    assert checker.cli() == 0
