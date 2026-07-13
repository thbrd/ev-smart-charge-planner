"""Home Assistant coordinator and local EV executor."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .ai import choose_candidate
from .const import (
    CONF_AI_API_KEY,
    CONF_AI_ENABLED,
    CONF_AI_MODE,
    CONF_AI_MODEL,
    CONF_BATTERY_CAPACITY,
    CONF_CHARGE_POWER,
    CONF_CHARGER_STATE_ENTITY,
    CONF_CHARGER_SWITCH_ENTITY,
    CONF_CHARGING_ENTITY,
    CONF_CONTROL_MODE,
    CONF_EFFICIENCY,
    CONF_ERE_RATE,
    CONF_PLUG_ENTITY,
    CONF_POWER_ENTITY,
    CONF_SESSION_ENERGY_ENTITY,
    CONF_SOC_ENTITY,
    CONF_SOLAR_FORECAST_ENTITY,
    CONF_SOLAR_NOW_ENTITY,
    CONF_TARIFF_ENTITY,
    CONF_TARIFF_PROVIDER,
    CONF_TARGET_ENTITY,
    CONF_TARGET_SOC,
    CONF_TELEGRAM_CHAT_ID,
    CONF_TELEGRAM_ENABLED,
    CONF_TELEGRAM_SERVICE,
    DEFAULTS,
    SETUP_ENTITY_KEYS,
    TELEGRAM_TEMPLATE_KEYS,
)
from .history import SessionHistory
from .discovery import discover_entities
from .config_helpers import (
    canonical_entry_storage,
    merged_entry_values,
    without_entity_options,
)
from .planner import make_plan, normalize_slots, number

_LOGGER = logging.getLogger(__name__)

SETUP_LABELS = {
    CONF_SOC_ENTITY: "Auto SoC",
    CONF_PLUG_ENTITY: "Auto aangesloten",
    CONF_CHARGING_ENTITY: "Auto laadstatus",
    CONF_TARGET_ENTITY: "Auto doelpercentage",
    CONF_CHARGER_STATE_ENTITY: "Laadpaalstatus",
    CONF_CHARGER_SWITCH_ENTITY: "Laadpaal aan/uit",
    CONF_POWER_ENTITY: "Laadvermogen",
    CONF_SESSION_ENERGY_ENTITY: "Sessie-energie",
    CONF_TARIFF_ENTITY: "Tarief + forecast",
    CONF_SOLAR_FORECAST_ENTITY: "Zonneforecast",
    CONF_SOLAR_NOW_ENTITY: "Zonnevermogen nu",
}
REQUIRED_SETUP_KEYS = {
    CONF_SOC_ENTITY,
    CONF_PLUG_ENTITY,
    CONF_CHARGER_STATE_ENTITY,
    CONF_CHARGER_SWITCH_ENTITY,
    CONF_TARIFF_ENTITY,
}


def state_value(hass: HomeAssistant, entity_id: str | None) -> Any:
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    return state.state if state else None


def attributes(hass: HomeAssistant, entity_id: str | None) -> dict[str, Any]:
    if not entity_id:
        return {}
    state = hass.states.get(entity_id)
    return dict(state.attributes) if state else {}


class EVSmartChargeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: Any) -> None:
        self.entry = entry
        data, options = canonical_entry_storage(entry.data, entry.options)
        if data != entry.data or options != entry.options:
            hass.config_entries.async_update_entry(entry, data=data, options=options)
        self.options = merged_entry_values(data, options)
        self.history = SessionHistory(hass, entry.entry_id)
        self._session: dict[str, Any] | None = None
        self._last_session: dict[str, Any] | None = None
        self._last_ai_reason = ""
        self.discovery_candidates: dict[str, list[dict[str, Any]]] = {}
        super().__init__(hass, logger=_LOGGER, name="EV Smart Charge Planner", update_interval=timedelta(seconds=30))

    async def async_initialize(self) -> None:
        self.discovery_candidates = discover_entities(self.hass, limit=None)
        await self.history.async_load()
        self._session = self.history.active_session
        if self.history.sessions:
            self._last_session = self.history.sessions[-1]
        if self.history.plan:
            self.data = {"plan": self.history.plan}
        await self.async_refresh()

    def async_set_options(self, values: dict[str, Any]) -> None:
        self.options = {**self.options, **values}
        self.hass.config_entries.async_update_entry(self.entry, options=self.options)
        self.async_set_updated_data(self.data)

    def async_update_options_from_entry(self) -> None:
        self.options = merged_entry_values(self.entry.data, self.entry.options)
        self.async_set_updated_data(self.data or {})

    def connection_checks(self, snapshot: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
        """Return a live, human-readable status for every configured source."""
        snapshot = snapshot or self.snapshot()
        tariff_slots = len(snapshot.get("tariff_slots") or [])
        checks: dict[str, dict[str, Any]] = {}
        for key in SETUP_ENTITY_KEYS:
            entity_id = self.options.get(key)
            required = key in REQUIRED_SETUP_KEYS
            base = {"label": SETUP_LABELS[key], "entity_id": entity_id, "required": required}
            if not entity_id:
                checks[key] = {
                    **base,
                    "status": "missing" if required else "optional",
                    "detail": "Niet gekoppeld" if required else "Niet gekoppeld (optioneel)",
                }
                continue
            state = self.hass.states.get(entity_id)
            if state is None:
                checks[key] = {**base, "status": "missing", "detail": "Entity bestaat niet"}
                continue
            value = state.state
            if value in ("unknown", "unavailable"):
                checks[key] = {**base, "status": "unavailable", "value": value, "detail": f"Geen bruikbare waarde ({value})"}
                continue
            status = "ok"
            detail = f"Beschikbaar: {value}"
            if key == CONF_TARIFF_ENTITY and not tariff_slots:
                status = "warning"
                detail = "Entity beschikbaar, maar geen forecastblokken gevonden"
            checks[key] = {**base, "status": status, "value": value, "detail": detail}
        return checks

    def setup_status(self, checks: dict[str, dict[str, Any]] | None = None) -> str:
        checks = checks or (self.data or {}).get("connection_checks") or self.connection_checks()
        if any(checks.get(key, {}).get("status") == "missing" for key in REQUIRED_SETUP_KEYS):
            return "needs_configuration"
        if any(checks.get(key, {}).get("status") != "ok" for key in REQUIRED_SETUP_KEYS):
            return "warning"
        return "ready"

    def async_update_setup(self, values: dict[str, Any]) -> None:
        """Persist wizard-selected entities and safe control settings."""
        updates = {key: value for key, value in values.items() if value is not None}
        data = dict(self.entry.data)
        required = {CONF_SOC_ENTITY, CONF_PLUG_ENTITY, CONF_CHARGER_STATE_ENTITY, CONF_CHARGER_SWITCH_ENTITY, CONF_TARIFF_ENTITY}
        for key in (*SETUP_ENTITY_KEYS, CONF_TARIFF_PROVIDER, CONF_CONTROL_MODE):
            if key not in updates:
                continue
            value = str(updates[key]).strip()
            if value:
                data[key] = value
            elif key not in required:
                data.pop(key, None)
        options = {
            **without_entity_options(self.entry.options),
            **{
                key: data[key]
                for key in (CONF_TARIFF_PROVIDER, CONF_CONTROL_MODE)
                if key in data
            },
        }
        self.hass.config_entries.async_update_entry(self.entry, data=data, options=options)
        self.options = merged_entry_values(data, options)
        snapshot = self.snapshot()
        self.async_set_updated_data({
            **(self.data or {}),
            "snapshot": snapshot,
            "connection_checks": self.connection_checks(snapshot),
            "aggregates": self.history.aggregates(),
        })

    async def async_test_connection(self) -> dict[str, Any]:
        """Validate configured sources without touching the charger."""
        self.discovery_candidates = discover_entities(self.hass, limit=None)
        snapshot = self.snapshot()
        checks = self.connection_checks(snapshot)
        tariff_count = len(snapshot.get("tariff_slots") or [])
        failed = [key for key in REQUIRED_SETUP_KEYS if checks.get(key, {}).get("status") != "ok"]
        status = "ready" if not failed else "warning"
        if status == "ready":
            reason = "Alle vereiste bronnen en de tariefforecast zijn beschikbaar."
        else:
            labels = [SETUP_LABELS.get(key, key) for key in failed]
            reason = "Controleer: " + ", ".join(labels)
        result = {"status": status, "reason": reason, "checks": checks, "tariff_slots": tariff_count}
        self.data = {**(self.data or {}), "connection_test": result, "connection_checks": checks, "snapshot": snapshot}
        self.async_set_updated_data(self.data)
        return result

    def snapshot(self) -> dict[str, Any]:
        config = self.options
        tariff_entity = config.get(CONF_TARIFF_ENTITY)
        tariff_attrs = attributes(self.hass, tariff_entity)
        raw_tariff_slots = tariff_attrs.get(
            "forecast",
            tariff_attrs.get("prices", tariff_attrs.get("hourly", tariff_attrs.get("tariffs", []))),
        )
        tariff_slots = [
            {
                "start_at": slot["start"].isoformat(),
                "end_at": slot["end"].isoformat(),
                "eur_per_kwh": round(slot["price"], 7),
            }
            for slot in normalize_slots(raw_tariff_slots)
        ]
        return {
            "ev": {
                "soc_percent": number(state_value(self.hass, config.get(CONF_SOC_ENTITY))),
                "plug_state": state_value(self.hass, config.get(CONF_PLUG_ENTITY)),
                "charging_state": state_value(self.hass, config.get(CONF_CHARGING_ENTITY)),
                "target_state": state_value(self.hass, config.get(CONF_TARGET_ENTITY)),
            },
            "charger": {
                "state": state_value(self.hass, config.get(CONF_CHARGER_STATE_ENTITY)),
                "power_w": number(state_value(self.hass, config.get(CONF_POWER_ENTITY)), 0),
                "session_energy_kwh": number(state_value(self.hass, config.get(CONF_SESSION_ENERGY_ENTITY))),
                "switch_state": state_value(self.hass, config.get(CONF_CHARGER_SWITCH_ENTITY)),
            },
            "tariff_slots": tariff_slots,
            "current_tariff": number(state_value(self.hass, tariff_entity)),
            "solar_forecast_kwh": number(state_value(self.hass, config.get(CONF_SOLAR_FORECAST_ENTITY))),
            "solar_now_w": number(state_value(self.hass, config.get(CONF_SOLAR_NOW_ENTITY)), 0),
            "settings": {
                "battery_capacity_kwh": number(config.get(CONF_BATTERY_CAPACITY), DEFAULTS[CONF_BATTERY_CAPACITY]),
                "charge_power_kw": number(config.get(CONF_CHARGE_POWER), DEFAULTS[CONF_CHARGE_POWER]),
                "charge_efficiency": number(config.get(CONF_EFFICIENCY), DEFAULTS[CONF_EFFICIENCY]),
                "target_soc_percent": number(config.get(CONF_TARGET_SOC), DEFAULTS[CONF_TARGET_SOC]),
                "ere_rate_eur_per_kwh": number(config.get(CONF_ERE_RATE), DEFAULTS[CONF_ERE_RATE]),
            },
            "configuration": {
                key: config.get(key) for key in SETUP_ENTITY_KEYS if config.get(key)
            } | {
                CONF_TARIFF_PROVIDER: config.get(CONF_TARIFF_PROVIDER, DEFAULTS[CONF_TARIFF_PROVIDER]),
                CONF_CONTROL_MODE: config.get(CONF_CONTROL_MODE, DEFAULTS[CONF_CONTROL_MODE]),
            },
        }

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            snapshot = self.snapshot()
            data = self.data or {}
            data = {**data, "snapshot": snapshot, "connection_checks": self.connection_checks(snapshot), "session": self._live_session(snapshot), "aggregates": self.history.aggregates()}
            await self._async_execute_if_due(data)
            return data
        except Exception as err:
            raise UpdateFailed(str(err)) from err

    async def async_create_plan(self, mode: str = "flex", deadline: str | None = None, target_soc: float | None = None, dry_run: bool = False) -> dict[str, Any]:
        snapshot = self.snapshot()
        plan = make_plan(snapshot, mode, deadline, target_soc)
        if self.options.get(CONF_AI_ENABLED) and self.options.get(CONF_AI_MODE) == "choose_candidate" and not dry_run:
            advice = await choose_candidate(self.hass, str(self.options.get(CONF_AI_API_KEY, "")), str(self.options.get(CONF_AI_MODEL, DEFAULTS[CONF_AI_MODEL])), plan.get("candidates", []))
            if advice:
                self._last_ai_reason = advice["reason"]
                plan["selected"] = next(item for item in plan["candidates"] if item["id"] == advice["chosen_candidate"])
                plan["reason"] = advice["reason"]
            else:
                plan["reason"] = "AI niet beschikbaar; lokaal goedkoopste geldige plan gebruikt."
        if not dry_run:
            self.history.plan = plan
            await self.history.async_save_state(plan, self._session)
            self.data = {**(self.data or {}), "plan": plan, "snapshot": snapshot, "aggregates": self.history.aggregates()}
            self.async_set_updated_data(self.data)
            await self.async_send_telegram("plan")
        return plan

    async def async_simulate_plan(
        self,
        mode: str = "flex",
        target_soc: float | None = None,
        deadline: str | None = None,
        label: str | None = None,
    ) -> dict[str, Any]:
        """Calculate a visible test result without saving or switching anything."""
        snapshot = self.snapshot()
        plan = make_plan(snapshot, mode, deadline, target_soc)
        plan["test_label"] = label or mode
        self.data = {
            **(self.data or {}),
            "simulation": plan,
            "snapshot": snapshot,
            "aggregates": self.history.aggregates(),
        }
        self.async_set_updated_data(self.data)
        return plan

    class _TelegramValues(dict):
        def __missing__(self, key):
            return "—"

    def _telegram_values(self) -> dict[str, str]:
        data = self.data or {}
        snapshot = data.get("snapshot") or self.snapshot()
        ev = snapshot.get("ev", {})
        charger = snapshot.get("charger", {})
        settings = snapshot.get("settings", {})
        plan = data.get("plan") or {}
        selected = plan.get("selected") or {}
        session = data.get("session") or self._last_session or {}

        def value(source: dict[str, Any], key: str, fallback: Any = "—") -> str:
            raw = source.get(key, fallback)
            if raw is None or raw == "":
                raw = fallback
            if isinstance(raw, float):
                return f"{raw:.2f}"
            return str(raw)

        return {
            "status": value(plan, "status", "idle"),
            "soc": value(ev, "soc_percent"),
            "target": value(plan, "target_soc_percent", settings.get("target_soc_percent", 95)),
            "charger_state": value(charger, "state"),
            "plan_start": value(selected, "start_at"),
            "plan_end": value(selected, "end_at"),
            "plan_kwh": value(selected, "kwh", 0),
            "plan_cost": value(selected, "cost_eur", 0),
            "plan_ere": value(selected, "ere_eur", 0),
            "plan_net": value(selected, "net_eur", 0),
            "session_kwh": value(session, "kwh", 0),
            "session_cost": value(session, "cost", 0),
            "session_ere": value(session, "ere", 0),
            "session_net": value(session, "net", 0),
        }

    async def async_send_telegram(self, event: str = "test", override_message: str | None = None) -> bool:
        if not self.options.get(CONF_TELEGRAM_ENABLED):
            return False
        service = str(self.options.get(CONF_TELEGRAM_SERVICE, "")).strip()
        chat_id = str(self.options.get(CONF_TELEGRAM_CHAT_ID, "")).strip()
        if "." not in service or not chat_id:
            _LOGGER.warning("Telegram is enabled but service or chat ID is missing")
            return False
        template_key = TELEGRAM_TEMPLATE_KEYS.get(event, TELEGRAM_TEMPLATE_KEYS["test"])
        template = override_message if override_message is not None else str(self.options.get(template_key, DEFAULTS[template_key]))
        try:
            message = template.format_map(self._TelegramValues(self._telegram_values()))
        except ValueError:
            _LOGGER.warning("Invalid Telegram template for event %s; sending it unchanged", event)
            message = template
        domain, service_name = service.split(".", 1)
        service_data: dict[str, Any] = {"message": message}
        if domain == "telegram_bot":
            service_data["chat_id"] = chat_id
        else:
            service_data["target"] = chat_id
        try:
            await self.hass.services.async_call(domain, service_name, service_data, blocking=False)
        except Exception as err:  # Telegram must never interrupt charging logic.
            _LOGGER.warning("Telegram message could not be sent: %s", err)
            return False
        return True

    def _safe_to_start(self, snapshot: dict[str, Any], target_soc: float | None = None) -> bool:
        ev = snapshot["ev"]
        charger = snapshot["charger"]
        plug = str(ev.get("plug_state") or "").lower()
        charger_state = str(charger.get("state") or "").lower()
        soc = number(ev.get("soc_percent"))
        target = number(target_soc, None)
        if target is None:
            target = number(snapshot["settings"].get("target_soc_percent"), 95)
        plugged = plug in {"connected", "on", "true", "suspended", "charging"} or charger_state in {"suspended", "charging"}
        return plugged and soc is not None and soc < target and charger_state not in {"no_ev_connected", "fault", "error", "invalid"}

    async def _async_execute_if_due(self, data: dict[str, Any]) -> None:
        if self.options.get(CONF_CONTROL_MODE, DEFAULTS[CONF_CONTROL_MODE]) != "hacs":
            return
        snapshot = data["snapshot"]
        if self._session:
            plan = data.get("plan") or {}
            target = number(plan.get("target_soc_percent"), None)
            if target is None:
                target = number(snapshot["settings"].get("target_soc_percent"), 95)
            target = target or 95
            soc = number(snapshot["ev"].get("soc_percent"))
            if soc is not None and soc >= target:
                switch = self.options.get(CONF_CHARGER_SWITCH_ENTITY)
                await self.hass.services.async_call("switch", "turn_off", {"entity_id": switch}, blocking=False)
                await self._async_finish_session("target_reached")
                return
        plan = data.get("plan") or {}
        selected = plan.get("selected") or {}
        if plan.get("status") != "planned" or not selected:
            return
        start = datetime.fromisoformat(selected["start_at"])
        if datetime.now(start.tzinfo) < start:
            return
        plan = (self.data or {}).get("plan") or {}
        plan_target = number(plan.get("target_soc_percent"), None)
        if not self._safe_to_start(snapshot, plan_target):
            return
        switch = self.options.get(CONF_CHARGER_SWITCH_ENTITY)
        if switch and state_value(self.hass, switch) != "on":
            await self.hass.services.async_call("switch", "turn_on", {"entity_id": switch}, blocking=False)
        if self._session is None:
            self._session = {"started_at": datetime.now().astimezone().isoformat(), "baseline_kwh": snapshot["charger"].get("session_energy_kwh") or 0}
            self.history.active_session = self._session
            await self.history.async_save_state(self.history.plan, self._session)

    def _live_session(self, snapshot: dict[str, Any]) -> dict[str, Any] | None:
        if not self._session:
            return None
        current = snapshot["charger"].get("session_energy_kwh") or 0
        kwh = max(0.0, current - float(self._session.get("baseline_kwh", 0)))
        selected = ((self.data or {}).get("plan") or {}).get("selected") or {}
        planned_kwh = float(selected.get("kwh", 0)) if selected else 0.0
        cost = min(1.0, kwh / planned_kwh) * float(selected.get("cost_eur", 0)) if selected and planned_kwh > 0 else 0.0
        ere = round(kwh * float(self.options.get(CONF_ERE_RATE, 0.12)), 2)
        return {"kwh": round(kwh, 3), "cost": round(cost, 2), "ere": ere, "net": round(cost - ere, 2)}

    async def async_start(self) -> None:
        if self.options.get(CONF_CONTROL_MODE, DEFAULTS[CONF_CONTROL_MODE]) != "hacs":
            raise ValueError("HACS-besturing staat uit; Node-RED blijft de laadpaal besturen.")
        snapshot = self.snapshot()
        plan = (self.data or {}).get("plan") or {}
        plan_target = number(plan.get("target_soc_percent"), None)
        if not self._safe_to_start(snapshot, plan_target):
            await self.async_send_telegram("blocked")
            raise ValueError("Start geblokkeerd: auto of laadpaal is niet veilig aangesloten.")
        switch = self.options.get(CONF_CHARGER_SWITCH_ENTITY)
        await self.hass.services.async_call("switch", "turn_on", {"entity_id": switch}, blocking=True)
        self._session = {"started_at": datetime.now().astimezone().isoformat(), "baseline_kwh": snapshot["charger"].get("session_energy_kwh") or 0}
        self.history.active_session = self._session
        await self.history.async_save_state(self.history.plan, self._session)
        self.data = {**(self.data or {}), "snapshot": snapshot, "session": self._live_session(snapshot)}
        self.async_set_updated_data(self.data)
        await self.async_send_telegram("start")

    async def async_stop(self, reason: str = "manual") -> None:
        if self.options.get(CONF_CONTROL_MODE, DEFAULTS[CONF_CONTROL_MODE]) != "hacs":
            raise ValueError("HACS-besturing staat uit; Node-RED blijft de laadpaal besturen.")
        switch = self.options.get(CONF_CHARGER_SWITCH_ENTITY)
        await self.hass.services.async_call("switch", "turn_off", {"entity_id": switch}, blocking=True)
        await self._async_finish_session(reason)

    async def _async_finish_session(self, reason: str) -> None:
        if not self._session:
            return
        snapshot = self.snapshot()
        current = snapshot["charger"].get("session_energy_kwh") or 0
        kwh = max(0.0, current - float(self._session.get("baseline_kwh", 0)))
        selected = ((self.data or {}).get("plan") or {}).get("selected") or {}
        planned_kwh = float(selected.get("kwh", 0)) if selected else 0.0
        cost = min(1.0, kwh / planned_kwh) * float(selected.get("cost_eur", 0)) if selected and planned_kwh > 0 else 0.0
        ere = round(kwh * float(self.options.get(CONF_ERE_RATE, 0.12)), 2)
        completed = {"started_at": self._session["started_at"], "stopped_at": datetime.now().astimezone().isoformat(), "kwh": round(kwh, 3), "cost": round(cost, 2), "ere": ere, "net": round(cost - ere, 2), "reason": reason}
        await self.history.async_add(completed)
        self._last_session = completed
        self._session = None
        self.history.plan = None
        self.history.active_session = None
        await self.history.async_save_state(None, None)
        if self.data:
            self.data["snapshot"] = snapshot
            self.data["aggregates"] = self.history.aggregates()
            self.data["plan"] = None
            self.data["session"] = None
            self.async_set_updated_data(self.data)
        await self.async_send_telegram("stop" if reason == "service_stop" else "done")

    async def async_reset(self) -> None:
        self._session = None
        self.history.plan = None
        self.history.active_session = None
        await self.history.async_save_state(None, None)
        if self.data:
            self.data["plan"] = None
            self.async_set_updated_data(self.data)
