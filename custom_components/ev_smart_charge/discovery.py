"""Best-effort entity discovery for the setup wizard.

Discovery is only a convenience layer. The selected entity IDs remain editable
and the planner never assumes a brand-specific entity name.
"""

from __future__ import annotations

from typing import Any


DISCOVERY_FIELDS = {
    "soc_entity": ("sensor", ("soc", "state of charge", "battery"), ("%",)),
    "plug_entity": (("binary_sensor", "sensor"), ("plug", "connected", "vehicle", "ev"), ()),
    "charging_entity": (("binary_sensor", "sensor"), ("charging", "charge state", "in_progress"), ()),
    "target_entity": (("select",), ("target", "charge limit", "charge"), ()),
    "charger_state_entity": (("sensor", "binary_sensor"), ("charger", "peblar", "zaptec", "wallbox", "state"), ()),
    "charger_switch_entity": (("switch",), ("charger", "charge", "peblar", "zaptec", "wallbox"), ()),
    "power_entity": (("sensor",), ("charge power", "charging power", "power", "charger"), ("W", "kW")),
    "session_energy_entity": (("sensor",), ("session", "energy", "charged", "charger"), ("kWh",)),
    "tariff_entity": (("sensor",), ("tariff", "electricity", "price", "zonneplan", "tibber", "anwb"), ("EUR/kWh", "€/kWh")),
    "solar_forecast_entity": (("sensor",), ("solar", "forecast", "production", "yield"), ("kWh",)),
    "solar_now_entity": (("sensor",), ("solar", "power", "production", "inverter", "p1"), ("W", "kW")),
}


def _state_text(state: Any) -> str:
    attributes = getattr(state, "attributes", {}) or {}
    parts = [
        str(getattr(state, "entity_id", "")),
        str(attributes.get("friendly_name", "")),
        str(attributes.get("device_class", "")),
        str(attributes.get("unit_of_measurement", "")),
        " ".join(str(key) for key in attributes),
    ]
    return " ".join(parts).lower()


def discover_entities(hass: Any, limit: int | None = 8) -> dict[str, list[dict[str, Any]]]:
    """Return ranked entity candidates grouped by configuration field."""
    states = hass.states.async_all() if hasattr(hass.states, "async_all") else list(hass.states)
    result: dict[str, list[dict[str, Any]]] = {}
    for field, (domains, keywords, units) in DISCOVERY_FIELDS.items():
        candidates: list[dict[str, Any]] = []
        for state in states:
            entity_id = getattr(state, "entity_id", "")
            if not entity_id or entity_id.split(".", 1)[0] not in domains:
                continue
            text = _state_text(state)
            attributes = getattr(state, "attributes", {}) or {}
            score = 0
            score += sum(3 for keyword in keywords if keyword in text)
            unit = str(attributes.get("unit_of_measurement", ""))
            score += sum(2 for expected in units if expected.lower() in unit.lower())
            if field == "tariff_entity" and isinstance(attributes.get("forecast"), list):
                score += 8
            if field == "solar_forecast_entity" and "forecast" in text:
                score += 3
            if score <= 0:
                continue
            candidates.append({
                "entity_id": entity_id,
                "name": attributes.get("friendly_name", entity_id),
                "score": score,
                "reason": _reason(field, attributes, unit),
            })
        candidates.sort(key=lambda item: (-item["score"], item["entity_id"]))
        result[field] = candidates if limit is None else candidates[:limit]
    return result


def _reason(field: str, attributes: dict[str, Any], unit: str) -> str:
    if field == "tariff_entity" and isinstance(attributes.get("forecast"), list):
        return "forecast-attribuut gevonden"
    if unit:
        return f"eenheid {unit}"
    return "naam of apparaatkenmerken matchen"


def best_entity(hass: Any, field: str) -> str | None:
    candidates = discover_entities(hass).get(field, [])
    return candidates[0]["entity_id"] if candidates else None
