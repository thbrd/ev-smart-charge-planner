"""AI enable switch."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_AI_ENABLED, DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([EVAIEnabled(hass.data[DOMAIN][entry.entry_id])])


class EVAIEnabled(CoordinatorEntity, SwitchEntity):
    _attr_name = "AI gebruiken"
    _attr_has_entity_name = True

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_ai_enabled"
        self._attr_suggested_object_id = "ev_smart_charge_ai_enabled"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.entry.entry_id)},
            "name": "EV Smart Charge Planner",
            "manufacturer": "EV Smart Charge Planner",
        }

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.options.get(CONF_AI_ENABLED, False))

    async def async_turn_on(self, **kwargs):
        self.coordinator.async_set_options({CONF_AI_ENABLED: True})
        await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs):
        self.coordinator.async_set_options({CONF_AI_ENABLED: False})
        await self.coordinator.async_refresh()
