"""Sensors exposed by the integration."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EVSmartChargeCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EVSensor(coordinator, key, label, unit) for key, label, unit in SENSOR_DEFINITIONS])


SENSOR_DEFINITIONS = [
    ("status", "Status", None),
    ("soc", "SoC", "%"),
    ("target_soc", "Doel SoC", "%"),
    ("power_kw", "Laadvermogen", "kW"),
    ("current_tariff", "Huidig tarief", "EUR/kWh"),
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
        aggregates = data.get("aggregates", {})
        if self.key == "status":
            return (data.get("plan") or {}).get("status", "idle")
        if self.key == "soc":
            return ev.get("soc_percent")
        if self.key == "target_soc":
            return (data.get("plan") or {}).get("target_soc_percent", snapshot.get("settings", {}).get("target_soc_percent"))
        if self.key == "power_kw":
            return round((charger.get("power_w") or 0) / 1000, 3)
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
        if self.key.startswith("session_"):
            return (data.get("session") or {}).get(self.key.removeprefix("session_"))
        for period in ("today", "month", "year"):
            if self.key.startswith(period + "_"):
                return aggregates.get(period, {}).get(self.key.removeprefix(period + "_"))
        if self.key == "current_tariff":
            return snapshot.get("current_tariff")
        return None
