"""Editable integration settings; no manual input_number helpers needed."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_BATTERY_CAPACITY, CONF_CHARGE_POWER, CONF_EFFICIENCY, CONF_ERE_RATE, CONF_TARGET_SOC, DOMAIN


SETTINGS = [
    (CONF_TARGET_SOC, "Doelpercentage", 50, 100, 5, "%"),
    (CONF_CHARGE_POWER, "Laadvermogen", 1, 50, 0.1, "kW"),
    (CONF_BATTERY_CAPACITY, "Accucapaciteit", 1, 200, 0.1, "kWh"),
    (CONF_EFFICIENCY, "Laadefficiëntie", 0.5, 1, 0.01, None),
    (CONF_ERE_RATE, "ERE per kWh", -1, 2, 0.01, "EUR/kWh"),
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EVNumber(coordinator, *item) for item in SETTINGS])


class EVNumber(CoordinatorEntity, NumberEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, key, label, minimum, maximum, step, unit):
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
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        return float(self.coordinator.options.get(self.key, 0))

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.async_set_options({self.key: value})
        await self.coordinator.async_refresh()
