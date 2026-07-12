"""Editable Telegram message templates."""

from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_TELEGRAM_TEMPLATE_BLOCKED,
    CONF_TELEGRAM_TEMPLATE_DONE,
    CONF_TELEGRAM_TEMPLATE_PLAN,
    CONF_TELEGRAM_TEMPLATE_START,
    CONF_TELEGRAM_TEMPLATE_STOP,
    CONF_TELEGRAM_TEMPLATE_TEST,
    DOMAIN,
    DEFAULTS,
)


TEMPLATES = [
    (CONF_TELEGRAM_TEMPLATE_TEST, "Telegram testbericht"),
    (CONF_TELEGRAM_TEMPLATE_PLAN, "Telegram planbericht"),
    (CONF_TELEGRAM_TEMPLATE_START, "Telegram startbericht"),
    (CONF_TELEGRAM_TEMPLATE_DONE, "Telegram klaarbericht"),
    (CONF_TELEGRAM_TEMPLATE_STOP, "Telegram stopbericht"),
    (CONF_TELEGRAM_TEMPLATE_BLOCKED, "Telegram veiligheidsbericht"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EVTelegramTemplate(coordinator, key, name) for key, name in TEMPLATES])


class EVTelegramTemplate(CoordinatorEntity, TextEntity):
    _attr_has_entity_name = True
    _attr_mode = TextMode.TEXT
    _attr_native_min_len = 0
    _attr_native_max_len = 2048

    def __init__(self, coordinator, key: str, label: str) -> None:
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

    @property
    def native_value(self) -> str:
        return str(self.coordinator.options.get(self.key, DEFAULTS[self.key]))

    async def async_set_value(self, value: str) -> None:
        self.coordinator.async_set_options({self.key: value})
        await self.coordinator.async_refresh()
