"""UI configuration for EV Smart Charge Planner."""

from __future__ import annotations

import voluptuous as vol
from typing import Any
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .discovery import discover_entities
from .const import (
    AI_MODES,
    CONTROL_MODES,
    CONF_AI_API_KEY,
    CONF_AI_ENABLED,
    CONF_AI_MODE,
    CONF_AI_MODEL,
    CONF_BATTERY_CAPACITY,
    CONF_CHARGE_POWER,
    CONF_CONTROL_MODE,
    CONF_CHARGER_STATE_ENTITY,
    CONF_CHARGER_SWITCH_ENTITY,
    CONF_CHARGING_ENTITY,
    CONF_EFFICIENCY,
    CONF_ERE_RATE,
    CONF_PLUG_ENTITY,
    CONF_POWER_ENTITY,
    CONF_PROFILE_NAME,
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
    DOMAIN,
    TARIFF_PROVIDERS,
)


def entity(domain: str | list[str]) -> Any:
    config = selector.EntitySelectorConfig(domain=domain)
    return selector.EntitySelector(config)


def api_key_selector() -> Any:
    return selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD))


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, object] = {}

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_entities()
        return self.async_show_form(step_id="user", data_schema=vol.Schema({vol.Required(CONF_PROFILE_NAME, default="Mijn EV") : str}))

    async def async_step_entities(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_energy()
        suggestions = discover_entities(self.hass)

        def field(key: str, domain: str | list[str], required: bool = False):
            default = (suggestions.get(key) or [{}])[0].get("entity_id")
            if required:
                return vol.Required(key, default=default) if default else vol.Required(key)
            return vol.Optional(key, default=default) if default else vol.Optional(key)

        schema = vol.Schema({
            field(CONF_SOC_ENTITY, "sensor", True): entity("sensor"),
            field(CONF_PLUG_ENTITY, ["binary_sensor", "sensor"], True): entity(["binary_sensor", "sensor"]),
            field(CONF_CHARGING_ENTITY, ["binary_sensor", "sensor"]): entity(["binary_sensor", "sensor"]),
            field(CONF_TARGET_ENTITY, "select"): entity("select"),
            field(CONF_CHARGER_STATE_ENTITY, ["sensor", "binary_sensor"], True): entity(["sensor", "binary_sensor"]),
            field(CONF_CHARGER_SWITCH_ENTITY, "switch", True): entity("switch"),
            field(CONF_POWER_ENTITY, "sensor"): entity("sensor"),
            field(CONF_SESSION_ENERGY_ENTITY, "sensor"): entity("sensor"),
        })
        return self.async_show_form(step_id="entities", data_schema=schema)

    async def async_step_energy(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_options()
        suggestions = discover_entities(self.hass)

        def field(key: str, required: bool = False):
            default = (suggestions.get(key) or [{}])[0].get("entity_id")
            if required:
                return vol.Required(key, default=default) if default else vol.Required(key)
            return vol.Optional(key, default=default) if default else vol.Optional(key)

        schema = vol.Schema({
            field(CONF_TARIFF_ENTITY, True): entity("sensor"),
            vol.Required(CONF_TARIFF_PROVIDER, default=DEFAULTS[CONF_TARIFF_PROVIDER]): vol.In(TARIFF_PROVIDERS),
            field(CONF_SOLAR_FORECAST_ENTITY): entity("sensor"),
            field(CONF_SOLAR_NOW_ENTITY): entity("sensor"),
        })
        return self.async_show_form(step_id="energy", data_schema=schema)

    async def async_step_options(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title=str(self._data[CONF_PROFILE_NAME]), data=self._data)
        schema = vol.Schema({
            vol.Required(CONF_BATTERY_CAPACITY, default=DEFAULTS[CONF_BATTERY_CAPACITY]): vol.Coerce(float),
            vol.Required(CONF_CHARGE_POWER, default=DEFAULTS[CONF_CHARGE_POWER]): vol.Coerce(float),
            vol.Required(CONF_EFFICIENCY, default=DEFAULTS[CONF_EFFICIENCY]): vol.Coerce(float),
            vol.Required(CONF_TARGET_SOC, default=DEFAULTS[CONF_TARGET_SOC]): vol.Coerce(float),
            vol.Required(CONF_ERE_RATE, default=DEFAULTS[CONF_ERE_RATE]): vol.Coerce(float),
            vol.Required(CONF_CONTROL_MODE, default=DEFAULTS[CONF_CONTROL_MODE]): vol.In(CONTROL_MODES),
            vol.Optional(CONF_AI_ENABLED, default=False): bool,
            vol.Optional(CONF_AI_MODE, default=DEFAULTS[CONF_AI_MODE]): vol.In(AI_MODES),
            vol.Optional(CONF_AI_API_KEY, default=""): api_key_selector(),
            vol.Optional(CONF_AI_MODEL, default=DEFAULTS[CONF_AI_MODEL]): str,
            vol.Optional(CONF_TELEGRAM_ENABLED, default=DEFAULTS[CONF_TELEGRAM_ENABLED]): bool,
            vol.Optional(CONF_TELEGRAM_SERVICE, default=DEFAULTS[CONF_TELEGRAM_SERVICE]): str,
            vol.Optional(CONF_TELEGRAM_CHAT_ID, default=DEFAULTS[CONF_TELEGRAM_CHAT_ID]): str,
        })
        return self.async_show_form(step_id="options", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        values = {**DEFAULTS, **self.config_entry.data, **self.config_entry.options}
        schema = vol.Schema({
            vol.Required(CONF_BATTERY_CAPACITY, default=values[CONF_BATTERY_CAPACITY]): vol.Coerce(float),
            vol.Required(CONF_CHARGE_POWER, default=values[CONF_CHARGE_POWER]): vol.Coerce(float),
            vol.Required(CONF_EFFICIENCY, default=values[CONF_EFFICIENCY]): vol.Coerce(float),
            vol.Required(CONF_TARGET_SOC, default=values[CONF_TARGET_SOC]): vol.Coerce(float),
            vol.Required(CONF_ERE_RATE, default=values[CONF_ERE_RATE]): vol.Coerce(float),
            vol.Required(CONF_CONTROL_MODE, default=values[CONF_CONTROL_MODE]): vol.In(CONTROL_MODES),
            vol.Required(CONF_TARIFF_PROVIDER, default=values[CONF_TARIFF_PROVIDER]): vol.In(TARIFF_PROVIDERS),
            vol.Optional(CONF_AI_ENABLED, default=values[CONF_AI_ENABLED]): bool,
            vol.Optional(CONF_AI_MODE, default=values[CONF_AI_MODE]): vol.In(AI_MODES),
            vol.Optional(CONF_AI_API_KEY, default=values.get(CONF_AI_API_KEY, "")): api_key_selector(),
            vol.Optional(CONF_AI_MODEL, default=values[CONF_AI_MODEL]): str,
            vol.Optional(CONF_TELEGRAM_ENABLED, default=values.get(CONF_TELEGRAM_ENABLED, DEFAULTS[CONF_TELEGRAM_ENABLED])): bool,
            vol.Optional(CONF_TELEGRAM_SERVICE, default=values.get(CONF_TELEGRAM_SERVICE, DEFAULTS[CONF_TELEGRAM_SERVICE])): str,
            vol.Optional(CONF_TELEGRAM_CHAT_ID, default=values.get(CONF_TELEGRAM_CHAT_ID, DEFAULTS[CONF_TELEGRAM_CHAT_ID])): str,
        })
        return self.async_show_form(step_id="init", data_schema=schema)
