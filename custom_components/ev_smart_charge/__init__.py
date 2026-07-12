"""EV Smart Charge Planner integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    DOMAIN,
    PLATFORMS,
    SERVICE_CREATE_PLAN,
    SERVICE_RESET,
    SERVICE_SIMULATE_PLAN,
    SERVICE_START,
    SERVICE_STATUS,
    SERVICE_STOP,
    SERVICE_TELEGRAM_SEND,
    SERVICE_TELEGRAM_TEST,
    TELEGRAM_EVENTS,
)
from .coordinator import EVSmartChargeCoordinator

SERVICE_SCHEMA = vol.Schema({vol.Optional("mode", default="flex"): vol.In(["today", "flex", "deadline"]), vol.Optional("deadline"): str, vol.Optional("target_soc"): vol.Coerce(float)})
TELEGRAM_SCHEMA = vol.Schema({vol.Optional("event", default="test"): vol.In(TELEGRAM_EVENTS), vol.Optional("message"): str})


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
            await active.async_create_plan(call.data["mode"], call.data.get("deadline"), call.data.get("target_soc"), dry_run=True)

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

        hass.services.async_register(DOMAIN, SERVICE_CREATE_PLAN, create_plan, schema=SERVICE_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_SIMULATE_PLAN, simulate_plan, schema=SERVICE_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_START, start)
        hass.services.async_register(DOMAIN, SERVICE_STOP, stop)
        hass.services.async_register(DOMAIN, SERVICE_RESET, reset)
        hass.services.async_register(DOMAIN, SERVICE_STATUS, status)
        hass.services.async_register(DOMAIN, SERVICE_TELEGRAM_TEST, telegram_test)
        hass.services.async_register(DOMAIN, SERVICE_TELEGRAM_SEND, telegram_send, schema=TELEGRAM_SCHEMA)
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
