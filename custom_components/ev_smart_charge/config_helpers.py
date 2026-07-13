"""Helpers for keeping entity connections canonical in a config entry."""

from __future__ import annotations

from typing import Any

from .const import DEFAULTS, SETUP_ENTITY_KEYS


def merged_entry_values(data: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    """Merge config-entry values while making entity data authoritative.

    Older releases could persist entity IDs in ``entry.options``. Entity
    connections belong to the config flow data, so current data must win over
    stale option values. Runtime settings remain option-authoritative.
    """
    values = {**DEFAULTS, **data, **options}
    for key in SETUP_ENTITY_KEYS:
        if key in data:
            values[key] = data[key]
    return values


def without_entity_options(options: dict[str, Any]) -> dict[str, Any]:
    """Remove legacy entity IDs from options so they cannot shadow data."""
    return {key: value for key, value in options.items() if key not in SETUP_ENTITY_KEYS}


def canonical_entry_storage(
    data: dict[str, Any], options: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return canonical config-entry storage for current and legacy entries.

    Entity connections are configuration data. Older releases could store
    them in options, so migrate those values only when data does not already
    contain a value. Runtime options remain in options.
    """
    canonical_data = dict(data)
    for key in SETUP_ENTITY_KEYS:
        if key not in canonical_data and options.get(key):
            canonical_data[key] = options[key]
    return canonical_data, without_entity_options(options)
