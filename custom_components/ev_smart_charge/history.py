"""Persistent session history and aggregates."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.helpers.storage import Store


class SessionHistory:
    def __init__(self, hass: Any, entry_id: str) -> None:
        self._store = Store(hass, 1, f"ev_smart_charge.{entry_id}")
        self.sessions: list[dict[str, Any]] = []
        self.plan: dict[str, Any] | None = None
        self.active_session: dict[str, Any] | None = None

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self.sessions = list(data.get("sessions", []))[-500:]
        self.plan = data.get("plan")
        self.active_session = data.get("active_session")

    async def async_save_state(self, plan: dict[str, Any] | None, active_session: dict[str, Any] | None) -> None:
        await self._store.async_save({"sessions": self.sessions[-500:], "plan": plan, "active_session": active_session})

    async def async_add(self, session: dict[str, Any]) -> None:
        self.sessions.append(session)
        self.sessions = self.sessions[-500:]
        await self._store.async_save({"sessions": self.sessions, "plan": self.plan, "active_session": self.active_session})

    def aggregates(self, now: datetime | None = None) -> dict[str, dict[str, float]]:
        now = now or datetime.now().astimezone()
        today = now.date().isoformat()
        month = now.strftime("%Y-%m")
        year = str(now.year)
        result = {key: {"kwh": 0.0, "cost": 0.0, "ere": 0.0, "net": 0.0, "sessions": 0} for key in ("today", "month", "year", "all")}
        for item in self.sessions:
            try:
                stopped = datetime.fromisoformat(item["stopped_at"]).astimezone()
            except (KeyError, TypeError, ValueError):
                continue
            keys = ["all"]
            if stopped.date().isoformat() == today:
                keys.append("today")
            if stopped.strftime("%Y-%m") == month:
                keys.append("month")
            if str(stopped.year) == year:
                keys.append("year")
            for key in keys:
                result[key]["kwh"] += float(item.get("kwh", 0))
                result[key]["cost"] += float(item.get("cost", 0))
                result[key]["ere"] += float(item.get("ere", 0))
                result[key]["net"] += float(item.get("net", 0))
                result[key]["sessions"] += 1
        return {key: {**values, "kwh": round(values["kwh"], 3), "cost": round(values["cost"], 2), "ere": round(values["ere"], 2), "net": round(values["net"], 2)} for key, values in result.items()}
