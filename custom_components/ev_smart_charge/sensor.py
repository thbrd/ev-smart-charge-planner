"""Sensors exposed by the integration."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_CONTROL_MODE, CONF_TARIFF_PROVIDER, DOMAIN, SETUP_ENTITY_KEYS
from .coordinator import EVSmartChargeCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EVSensor(coordinator, key, label, unit) for key, label, unit in SENSOR_DEFINITIONS])


SENSOR_DEFINITIONS = [
    ("status", "Status", None),
    ("soc", "SoC", "%"),
    ("target_soc", "Doel SoC", "%"),
    ("plug_state", "Auto aangesloten", None),
    ("charging_state", "Auto laadstatus", None),
    ("target_state", "Auto doelstatus", None),
    ("charger_state", "Laadpaalstatus", None),
    ("charger_switch_state", "Laadpaal switch", None),
    ("power_kw", "Laadvermogen", "kW"),
    ("session_energy_source_kwh", "Peblar sessie-energie", "kWh"),
    ("current_tariff", "Huidig tarief", "EUR/kWh"),
    ("tariff_slots", "Tariefblokken", None),
    ("solar_forecast_kwh", "Zonneforecast", "kWh"),
    ("solar_now_w", "Zonnevermogen nu", "W"),
    ("plan_start", "Plan start", None),
    ("plan_end", "Plan einde", None),
    ("plan_kwh", "Plan kWh", "kWh"),
    ("plan_cost", "Plan kosten", "EUR"),
    ("plan_ere", "Plan ERE", "EUR"),
    ("plan_net", "Plan netto", "EUR"),
    ("session_kwh", "Sessie kWh", "kWh"),
    ("session_cost", "Sessie kosten", "EUR"),
    ("session_ere", "Sessie ERE", "EUR"),
    ("session_net", "Sessie netto", "EUR"),
    ("today_kwh", "Vandaag kWh", "kWh"),
    ("today_cost", "Vandaag kosten", "EUR"),
    ("today_ere", "Vandaag ERE", "EUR"),
    ("today_net", "Vandaag netto", "EUR"),
    ("today_sessions", "Vandaag sessies", None),
    ("month_kwh", "Maand kWh", "kWh"),
    ("month_cost", "Maand kosten", "EUR"),
    ("month_ere", "Maand ERE", "EUR"),
    ("month_net", "Maand netto", "EUR"),
    ("month_sessions", "Maand sessies", None),
    ("year_kwh", "Jaar kWh", "kWh"),
    ("year_cost", "Jaar kosten", "EUR"),
    ("year_ere", "Jaar ERE", "EUR"),
    ("year_net", "Jaar netto", "EUR"),
    ("year_sessions", "Jaar sessies", None),
    ("setup_status", "Setupstatus", None),
    ("connection_test_status", "Verbindingstest status", None),
    ("connection_test_reason", "Verbindingstest toelichting", None),
    ("test_status", "Testplan status", None),
    ("test_mode", "Testplan modus", None),
    ("test_reason", "Testplan toelichting", None),
    ("test_start", "Testplan start", None),
    ("test_end", "Testplan einde", None),
    ("test_kwh", "Testplan kWh", "kWh"),
    ("test_cost", "Testplan kosten", "EUR"),
    ("test_ere", "Testplan ERE", "EUR"),
    ("test_net", "Testplan netto", "EUR"),
    ("test_windows", "Testprijsblokken", None),
]


class EVSensor(CoordinatorEntity[EVSmartChargeCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, key: str, label: str, unit: str | None) -> None:
        super().__init__(coordinator)
        self.key = key
        self._attr_name = label
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_suggested_object_id = f"ev_smart_charge_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.entry.entry_id)},
            "name": "EV Smart Charge Planner",
            "manufacturer": "EV Smart Charge Planner",
        }
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = "energy" if unit == "kWh" else None
        self._attr_state_class = "measurement" if unit in ("kWh", "kW", "%") else None

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        snapshot = data.get("snapshot", {})
        ev = snapshot.get("ev", {})
        charger = snapshot.get("charger", {})
        plan = (data.get("plan") or {}).get("selected") or {}
        simulation = data.get("simulation") or {}
        simulation_selected = simulation.get("selected") or {}
        aggregates = data.get("aggregates", {})
        connection_test = data.get("connection_test") or {}
        configuration = snapshot.get("configuration", {})
        if self.key == "setup_status":
            return self.coordinator.setup_status()
        if self.key == "connection_test_status":
            return connection_test.get("status", "not_run")
        if self.key == "connection_test_reason":
            return connection_test.get("reason", "Voer de verbindingstest uit vanuit het sidebar-panel.")
        if self.key == "status":
            return (data.get("plan") or {}).get("status", "idle")
        if self.key == "soc":
            return ev.get("soc_percent")
        if self.key == "target_soc":
            return (data.get("plan") or {}).get("target_soc_percent", snapshot.get("settings", {}).get("target_soc_percent"))
        if self.key == "plug_state":
            return ev.get("plug_state")
        if self.key == "charging_state":
            return ev.get("charging_state")
        if self.key == "target_state":
            return ev.get("target_state")
        if self.key == "charger_state":
            return charger.get("state")
        if self.key == "charger_switch_state":
            return charger.get("switch_state")
        if self.key == "power_kw":
            return round((charger.get("power_w") or 0) / 1000, 3)
        if self.key == "session_energy_source_kwh":
            return charger.get("session_energy_kwh")
        if self.key == "tariff_slots":
            return len(snapshot.get("tariff_slots") or [])
        if self.key == "solar_forecast_kwh":
            return snapshot.get("solar_forecast_kwh")
        if self.key == "solar_now_w":
            return snapshot.get("solar_now_w")
        if self.key == "plan_start":
            return plan.get("start_at")
        if self.key == "plan_end":
            return plan.get("end_at")
        if self.key == "plan_kwh":
            return plan.get("kwh")
        if self.key == "plan_cost":
            return plan.get("cost_eur")
        if self.key == "plan_ere":
            return plan.get("ere_eur")
        if self.key == "plan_net":
            return plan.get("net_eur")
        if self.key == "test_status":
            return simulation.get("status", "idle")
        if self.key == "test_mode":
            return simulation.get("test_label", "—")
        if self.key == "test_reason":
            return simulation.get("reason", "—")
        if self.key == "test_start":
            return simulation_selected.get("start_at")
        if self.key == "test_end":
            return simulation_selected.get("end_at")
        if self.key == "test_kwh":
            return simulation_selected.get("kwh")
        if self.key == "test_cost":
            return simulation_selected.get("cost_eur")
        if self.key == "test_ere":
            return simulation_selected.get("ere_eur")
        if self.key == "test_net":
            return simulation_selected.get("net_eur")
        if self.key == "test_windows":
            return len(simulation_selected.get("windows") or [])
        if self.key.startswith("session_"):
            return (data.get("session") or {}).get(self.key.removeprefix("session_"))
        for period in ("today", "month", "year"):
            if self.key.startswith(period + "_"):
                return aggregates.get(period, {}).get(self.key.removeprefix(period + "_"))
        if self.key == "current_tariff":
            return snapshot.get("current_tariff")
        return None

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        snapshot = data.get("snapshot", {})
        simulation = data.get("simulation") or {}
        selected = simulation.get("selected") or {}
        if self.key == "tariff_slots":
            return {"slots": snapshot.get("tariff_slots") or [], "count": len(snapshot.get("tariff_slots") or [])}
        if self.key == "test_windows":
            return {
                "mode": simulation.get("test_label", "—"),
                "reason": simulation.get("reason", "—"),
                "windows": selected.get("windows") or [],
                "candidates": simulation.get("candidates") or [],
            }
        if self.key == "test_status":
            return {"reason": simulation.get("reason", "—"), "mode": simulation.get("test_label", "—")}
        if self.key == "setup_status":
            configuration = {
                key: self.coordinator.options.get(key)
                for key in SETUP_ENTITY_KEYS
                if self.coordinator.options.get(key)
            }
            configuration.update(
                {
                    CONF_TARIFF_PROVIDER: self.coordinator.options.get(CONF_TARIFF_PROVIDER),
                    CONF_CONTROL_MODE: self.coordinator.options.get(CONF_CONTROL_MODE),
                }
            )
            return {
                # Read the canonical config-entry values directly. The
                # panel must not depend on a previously cached snapshot.
                "configuration": configuration,
                "candidates": self.coordinator.discovery_candidates,
                "checks": self.coordinator.connection_checks(snapshot),
                "auto_linked": self.coordinator.auto_linked_entities,
            }
        if self.key in ("connection_test_status", "connection_test_reason"):
            return (data.get("connection_test") or {}).get("checks", {})
        return None
