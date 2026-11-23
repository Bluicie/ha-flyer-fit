"""The Flyer FIT e-bike integration."""

from __future__ import annotations

from homeassistant.components import bluetooth
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import FlyerFitConfigEntry, FlyerFitCoordinator
from .parser import FitData

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: FlyerFitConfigEntry) -> bool:
    """Set up a bike from a config entry."""
    address = entry.unique_id
    assert address is not None
    coordinator = FlyerFitCoordinator(hass, entry, address)
    entry.runtime_data = coordinator
    # Don't read the bike during setup: a Bluetooth connection can take longer than
    # Home Assistant allows for setting up. Start empty (sensors restore their last
    # values) and read in the background.
    coordinator.async_set_updated_data(FitData())
    entry.async_create_background_task(
        hass, coordinator.async_refresh(), "flyer_fit_first_refresh"
    )

    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            coordinator.async_handle_advertisement,
            bluetooth.BluetoothCallbackMatcher(address=address, connectable=True),
            bluetooth.BluetoothScanningMode.PASSIVE,
        )
    )
    entry.async_on_unload(
        bluetooth.async_track_unavailable(
            hass, coordinator.async_handle_unavailable, address, connectable=True
        )
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FlyerFitConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
