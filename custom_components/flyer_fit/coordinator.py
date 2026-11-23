"""Coordinator that reads the bike while it is switched on."""

from __future__ import annotations

from collections import deque
import time
from typing import Any

from bleak.exc import BleakError

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .ble import read_bike
from .const import HISTORY_SIZE, LOGGER, MIN_SECONDS_BETWEEN_POLLS, UPDATE_INTERVAL
from .parser import FitData

type FlyerFitConfigEntry = ConfigEntry[FlyerFitCoordinator]


class FlyerFitCoordinator(DataUpdateCoordinator[FitData]):
    """Reads the bike when it is reachable and keeps the last values otherwise.

    The bike only advertises while its system is switched on. When it is off, the
    last read values are kept, so the battery level stays visible while parked.
    """

    config_entry: FlyerFitConfigEntry

    def __init__(self, hass: HomeAssistant, entry: FlyerFitConfigEntry, address: str) -> None:
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=f"Flyer FIT {address}",
            update_interval=UPDATE_INTERVAL,
            always_update=False,
        )
        self.address = address
        self.last_error: str | None = None
        self._last_poll = 0.0
        self._device_info_read = False
        self._heard = False
        self.history: deque[dict[str, Any]] = deque(maxlen=HISTORY_SIZE)

    def _remember(self, data: FitData) -> None:
        """Keep readings whose raw values changed, for decoding more fields.

        Shown in the diagnostics download. Device info is left out (it never
        changes), live notifications are kept when there are any.
        """
        raw = {k: v for k, v in data.raw.items() if "abab" in k}
        last = self.history[-1]["raw"] if self.history else None
        if raw == last and not data.notifications:
            return
        self.history.append(
            {
                "time": dt_util.now().isoformat(timespec="seconds"),
                "raw": raw,
                "notifications": data.notifications,
            }
        )

    @property
    def powered_on(self) -> bool:
        """Whether the bike is advertising, i.e. switched on."""
        return bluetooth.async_address_present(self.hass, self.address, connectable=True)

    @callback
    def async_handle_advertisement(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """The bike was heard: refresh soon if the last read is old enough."""
        if not self._heard:
            # Switched on: update the "powered on" sensor once, not per advertisement.
            self._heard = True
            self.async_update_listeners()
        if time.monotonic() - self._last_poll >= MIN_SECONDS_BETWEEN_POLLS:
            self._last_poll = time.monotonic()
            self.config_entry.async_create_background_task(
                self.hass, self.async_request_refresh(), "flyer_fit_refresh"
            )

    @callback
    def async_handle_unavailable(self, service_info: bluetooth.BluetoothServiceInfoBleak) -> None:
        """The bike stopped advertising (switched off)."""
        self._heard = False
        self.async_update_listeners()

    async def _async_update_data(self) -> FitData:
        previous = self.data or FitData()
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if ble_device is None:
            return previous

        self._last_poll = time.monotonic()
        try:
            data = await read_bike(ble_device, read_device_info=not self._device_info_read)
        except (BleakError, TimeoutError) as err:
            self.last_error = str(err)
            LOGGER.debug("Reading %s failed, keeping last values: %s", self.address, err)
            return previous

        self.last_error = None
        self._remember(data)
        if data.serial or data.model:
            self._device_info_read = True
        # Keep device info and fields the bike did not report this time.
        for field in ("manufacturer", "model", "serial", "battery", "range_km",
                      "voltage", "current", "power", "odometer_km", "riding_time_h",
                      "assist_mode"):
            if getattr(data, field) is None:
                setattr(data, field, getattr(previous, field))
        if not data.assist_modes:
            data.assist_modes = previous.assist_modes
        return data
