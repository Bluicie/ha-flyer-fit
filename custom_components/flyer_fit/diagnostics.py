"""Diagnostics: the raw values, so more fields can be decoded later."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .coordinator import FlyerFitConfigEntry
from .parser import SERIAL_CHAR

TO_REDACT = {"serial", SERIAL_CHAR, "address"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: FlyerFitConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    data = asdict(coordinator.data) if coordinator.data else {}
    if "raw" in data:
        data["raw"] = async_redact_data(data["raw"], TO_REDACT)
    return async_redact_data(
        {
            "address": coordinator.address,
            "powered_on": coordinator.powered_on,
            "last_error": coordinator.last_error,
            "data": data,
            "history": list(coordinator.history),
        },
        TO_REDACT,
    )
