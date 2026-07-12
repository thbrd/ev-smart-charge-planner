from datetime import datetime, timedelta, timezone

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("planner", Path(__file__).parents[1] / "custom_components/ev_smart_charge/planner.py")
planner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(planner)
make_plan = planner.make_plan


def snapshot():
    start = datetime(2026, 7, 13, 10, tzinfo=timezone.utc)
    return {
        "ev": {"soc_percent": 50},
        "settings": {"battery_capacity_kwh": 40, "charge_power_kw": 10, "charge_efficiency": 1, "target_soc_percent": 75, "ere_rate_eur_per_kwh": 0.12},
        "tariff_slots": [
            {"start_at": (start + timedelta(hours=i)).isoformat(), "end_at": (start + timedelta(hours=i + 1)).isoformat(), "eur_per_kwh": price}
            for i, price in enumerate([0.30, 0.10, 0.11, 0.40])
        ],
    }


def test_local_planner_selects_cheapest_valid_window():
    plan = make_plan(snapshot(), now=datetime(2026, 7, 13, 10, tzinfo=timezone.utc))
    assert plan["status"] == "planned"
    assert plan["selected"]["start_at"].startswith("2026-07-13T11:00")
    assert plan["selected"]["kwh"] == 10.0


def test_finished_when_target_reached():
    data = snapshot()
    data["ev"]["soc_percent"] = 80
    data["settings"]["target_soc_percent"] = 75
    assert make_plan(data)["status"] == "finished"
