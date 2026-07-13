"""EV Smart Charge Planner integration."""

from __future__ import annotations

from pathlib import Path

import voluptuous as vol
from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_CONTROL_MODE,
    CONF_TARIFF_PROVIDER,
    SETUP_ENTITY_KEYS,
    SERVICE_CREATE_PLAN,
    SERVICE_RESET,
    SERVICE_SIMULATE_PLAN,
    SERVICE_START,
    SERVICE_STATUS,
    SERVICE_STOP,
    SERVICE_TELEGRAM_SEND,
    SERVICE_TELEGRAM_TEST,
    SERVICE_TEST_FLEX,
    SERVICE_TEST_PLAN,
    SERVICE_TEST_CONNECTION,
    SERVICE_UPDATE_SETUP,
    TELEGRAM_EVENTS,
)
from .coordinator import EVSmartChargeCoordinator

SERVICE_SCHEMA = vol.Schema({vol.Optional("mode", default="flex"): vol.In(["today", "flex", "deadline"]), vol.Optional("deadline"): str, vol.Optional("target_soc"): vol.Coerce(float)})
TELEGRAM_SCHEMA = vol.Schema({vol.Optional("event", default="test"): vol.In(TELEGRAM_EVENTS), vol.Optional("message"): str})
TEST_SCHEMA = vol.Schema({vol.Optional("target_soc"): vol.Coerce(float)})
SETUP_SCHEMA = vol.Schema({vol.Optional(key): str for key in (*SETUP_ENTITY_KEYS, CONF_TARIFF_PROVIDER, CONF_CONTROL_MODE)})
PANEL_URL = "/ev_smart_charge_panel"
PANEL_PATH = "ev-smart-charge-panel"
PANEL_FRONTEND_URL = "ev-smart-charge"
PANEL_CACHE_VERSION = "0.5.6"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the local sidebar panel and its static frontend module."""
    panel_dir = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths([StaticPathConfig(PANEL_URL, str(panel_dir), False)])
    frontend.async_register_built_in_panel(
        hass,
        "custom",
        sidebar_title="EV Smart Charge",
        sidebar_icon="mdi:ev-station",
        frontend_url_path=PANEL_FRONTEND_URL,
        config={
            "_panel_custom": {
                "name": PANEL_PATH,
                "module_url": f"{PANEL_URL}/{PANEL_PATH}.js?v={PANEL_CACHE_VERSION}",
                "embed_iframe": False,
            }
        },
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = EVSmartChargeCoordinator(hass, entry)
    await coordinator.async_initialize()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    if not hass.services.has_service(DOMAIN, SERVICE_CREATE_PLAN):
        def coordinator_for_call() -> EVSmartChargeCoordinator:
            return next(iter(hass.data[DOMAIN].values()))

        async def create_plan(call: ServiceCall) -> None:
            active = coordinator_for_call()
            await active.async_create_plan(call.data["mode"], call.data.get("deadline"), call.data.get("target_soc"))

        async def simulate_plan(call: ServiceCall) -> None:
            active = coordinator_for_call()
            await active.async_simulate_plan(
                mode=call.data["mode"],
                deadline=call.data.get("deadline"),
                target_soc=call.data.get("target_soc"),
                label=f"simulate {call.data['mode']}",
            )

        async def start(call: ServiceCall) -> None:
            await coordinator_for_call().async_start()

        async def stop(call: ServiceCall) -> None:
            await coordinator_for_call().async_stop("service_stop")

        async def reset(call: ServiceCall) -> None:
            await coordinator_for_call().async_reset()

        async def status(call: ServiceCall) -> None:
            active = coordinator_for_call()
            await active.async_refresh()

        async def telegram_test(call: ServiceCall) -> None:
            await coordinator_for_call().async_send_telegram("test")

        async def telegram_send(call: ServiceCall) -> None:
            await coordinator_for_call().async_send_telegram(call.data["event"], call.data.get("message"))

        async def test_flex(call: ServiceCall) -> None:
            await coordinator_for_call().async_simulate_plan(
                mode="flex",
                target_soc=call.data.get("target_soc"),
                label="test flex",
            )

        async def test_plan(call: ServiceCall) -> None:
            await coordinator_for_call().async_simulate_plan(
                mode="flex",
                target_soc=call.data.get("target_soc"),
                label="test plan",
            )

        async def update_setup(call: ServiceCall) -> None:
            active = coordinator_for_call()
            active.async_update_setup(dict(call.data))
            await active.async_refresh()

        async def test_connection(call: ServiceCall) -> None:
            await coordinator_for_call().async_test_connection()

        hass.services.async_register(DOMAIN, SERVICE_CREATE_PLAN, create_plan, schema=SERVICE_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_SIMULATE_PLAN, simulate_plan, schema=SERVICE_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_START, start)
        hass.services.async_register(DOMAIN, SERVICE_STOP, stop)
        hass.services.async_register(DOMAIN, SERVICE_RESET, reset)
        hass.services.async_register(DOMAIN, SERVICE_STATUS, status)
        hass.services.async_register(DOMAIN, SERVICE_TELEGRAM_TEST, telegram_test)
        hass.services.async_register(DOMAIN, SERVICE_TELEGRAM_SEND, telegram_send, schema=TELEGRAM_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_TEST_FLEX, test_flex, schema=TEST_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_TEST_PLAN, test_plan, schema=TEST_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_UPDATE_SETUP, update_setup, schema=SETUP_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_TEST_CONNECTION, test_connection)
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator:
        coordinator.async_update_options_from_entry()
        await coordinator.async_refresh()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded
