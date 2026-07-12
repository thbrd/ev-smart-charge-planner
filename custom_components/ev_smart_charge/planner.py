"""Pure local EV planning logic. No Home Assistant or AI dependency."""

from __future__ import annotations

from datetime import datetime, timedelta
from math import ceil
from typing import Any


def number(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    if isinstance(value, dict):
        value = value.get("state", value.get("value"))
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000)
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def normalize_slots(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, dict):
        for key in ("forecast", "prices", "hourly", "tariffs", "slots"):
            if isinstance(raw.get(key), list):
                raw = raw[key]
                break
    if not isinstance(raw, list):
        return []

    result: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        start = parse_datetime(
            item.get("start_at", item.get("start", item.get("datetime", item.get("timestamp"))))
        )
        price = number(
            item.get(
                "eur_per_kwh",
                item.get("price_eur_per_kwh", item.get("price", item.get("value", item.get("tariff")))),
            )
        )
        if start is None or price is None:
            continue
        end = parse_datetime(item.get("end_at", item.get("end")))
        result.append({"start": start, "end": end, "price": price})

    result.sort(key=lambda slot: slot["start"])
    for index, slot in enumerate(result):
        if slot["end"] is None:
            next_start = result[index + 1]["start"] if index + 1 < len(result) else None
            slot["end"] = next_start or slot["start"] + timedelta(hours=1)
    return [slot for slot in result if slot["end"] > slot["start"]]


def _cost_window(start: datetime, end: datetime, kwh: float, power_kw: float, slots: list[dict[str, Any]]) -> dict[str, Any] | None:
    if end <= start or kwh <= 0 or power_kw <= 0:
        return None
    remaining = kwh
    total_cost = 0.0
    windows: list[dict[str, Any]] = []
    cursor = start

    for slot in slots:
        overlap_start = max(start, slot["start"])
        overlap_end = min(end, slot["end"])
        if overlap_end <= overlap_start:
            continue
        hours = (overlap_end - overlap_start).total_seconds() / 3600
        used = min(remaining, power_kw * hours)
        cost = used * slot["price"]
        total_cost += cost
        remaining -= used
        windows.append({
            "start_at": overlap_start.isoformat(),
            "end_at": overlap_end.isoformat(),
            "kwh": round(used, 3),
            "price_eur_per_kwh": round(slot["price"], 5),
            "cost_eur": round(cost, 3),
        })
        cursor = overlap_end
        if remaining <= 0.0001:
            break

    if remaining > 0.05:
        return None
    return {"cost_eur": round(total_cost, 2), "windows": windows}


def _candidate(start: datetime, duration: timedelta, kwh: float, power_kw: float, slots: list[dict[str, Any]], label: str) -> dict[str, Any] | None:
    end = start + duration
    calculation = _cost_window(start, end, kwh, power_kw, slots)
    if calculation is None:
        return None
    return {
        "id": label,
        "start_at": start.isoformat(),
        "end_at": end.isoformat(),
        "kwh": round(kwh, 3),
        "cost_eur": calculation["cost_eur"],
        "ere_eur": round(kwh * 0.12, 2),
        "net_eur": round(calculation["cost_eur"] - kwh * 0.12, 2),
        "windows": calculation["windows"],
    }


def build_candidates(snapshot: dict[str, Any], mode: str = "flex", deadline: str | None = None, now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or datetime.now().astimezone()
    settings = snapshot.get("settings", {})
    ev = snapshot.get("ev", {})
    slots = normalize_slots(snapshot.get("tariff_slots", []))
    soc = number(ev.get("soc_percent"), 0) or 0
    target = number(settings.get("target_soc_percent"), 95) or 95
    capacity = number(settings.get("battery_capacity_kwh"), 91) or 91
    efficiency = number(settings.get("charge_efficiency"), 0.9) or 0.9
    power_kw = number(settings.get("charge_power_kw"), 11) or 11
    needed = max(0.0, capacity * max(0.0, target - soc) / 100 / efficiency)

    if needed <= 0.01:
        return []
    duration = timedelta(hours=needed / power_kw)
    available = [slot for slot in slots if slot["end"] > now]
    if mode == "today":
        available = [slot for slot in available if slot["start"].date() == now.date()]

    limit: datetime | None = None
    if deadline:
        try:
            hh, mm = [int(part) for part in deadline.split(":", 1)]
            limit = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if limit <= now:
                limit += timedelta(days=1)
        except ValueError:
            limit = None
    if limit:
        available = [slot for slot in available if slot["start"] < limit]

    starts = []
    for slot in available:
        start = max(slot["start"], now)
        if limit and start + duration > limit:
            continue
        starts.append(start)

    candidates: list[dict[str, Any]] = []
    for start in starts:
        result = _candidate(start, duration, needed, power_kw, available, "candidate")
        if result:
            candidates.append(result)
    if not candidates:
        return []

    cheapest = min(candidates, key=lambda item: (item["cost_eur"], item["start_at"]))
    earliest = min(candidates, key=lambda item: item["start_at"])
    midday = min(candidates, key=lambda item: (abs(datetime.fromisoformat(item["start_at"]).hour - 13), item["cost_eur"]))
    unique: list[dict[str, Any]] = []
    for label, item in (("candidate_a", cheapest), ("candidate_b", midday), ("candidate_c", earliest)):
        copy = dict(item)
        copy["id"] = label
        copy["ere_eur"] = round(needed * (number(settings.get("ere_rate_eur_per_kwh"), 0.12) or 0.12), 2)
        copy["net_eur"] = round(copy["cost_eur"] - copy["ere_eur"], 2)
        if not any(existing["start_at"] == copy["start_at"] for existing in unique):
            unique.append(copy)
    return unique


def make_plan(snapshot: dict[str, Any], mode: str = "flex", deadline: str | None = None, target_soc: float | None = None, now: datetime | None = None) -> dict[str, Any]:
    snapshot = {**snapshot, "settings": {**snapshot.get("settings", {})}}
    if target_soc is not None:
        snapshot["settings"]["target_soc_percent"] = target_soc
    ev = snapshot.get("ev", {})
    target = number(snapshot["settings"].get("target_soc_percent"), 95) or 95
    soc = number(ev.get("soc_percent"), 0) or 0
    if soc >= target:
        return {"status": "finished", "reason": "De auto staat al op of boven het doel.", "candidates": [], "selected": None}
    candidates = build_candidates(snapshot, mode, deadline, now)
    if not candidates:
        return {"status": "unavailable", "reason": "Geen volledig geldig laadvenster beschikbaar.", "candidates": [], "selected": None}
    selected = candidates[0]
    return {
        "status": "planned",
        "mode": mode,
        "target_soc_percent": target,
        "current_soc_percent": soc,
        "deadline": deadline,
        "candidates": candidates,
        "selected": selected,
        "reason": "Lokaal berekend op basis van geldige tariefblokken.",
    }
