"""Read the bike over Bluetooth.

Only reads values and subscribes to notifications; never changes a bike setting.
"""

from __future__ import annotations

import asyncio

from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from .const import LOGGER
from .parser import DEVICE_INFO_CHARS, SIGMA_READ_CHARS, FitData, parse, sigma_char

LIVE_CHAR = sigma_char(0x01)
# Seconds to wait after subscribing before reading; the bike publishes clear
# values about a second after subscribing.
UNLOCK_DELAY = 1.5
OVERALL_TIMEOUT = 30

_AUTH_HINTS = ("auth", "encrypt", "insufficient", "not permitted", "0x05", "0x0f")


def _is_auth_error(err: Exception) -> bool:
    text = str(err).lower()
    return any(hint in text for hint in _AUTH_HINTS)


async def read_bike(ble_device: BLEDevice, read_device_info: bool) -> FitData:
    """Connect, read all known characteristics, disconnect, and parse."""
    raw: dict[str, bytes] = {}
    notifications: list[str] = []
    paired = False
    async with asyncio.timeout(OVERALL_TIMEOUT):
        client = await establish_connection(
            BleakClientWithServiceCache, ble_device, ble_device.name or ble_device.address
        )
        try:
            # The bike returns scrambled filler from every Sigma characteristic until a
            # client subscribes to notifications on characteristic 0001. Subscribing
            # (a standard descriptor write) makes it publish the real values.
            if client.services.get_characteristic(LIVE_CHAR) is not None:
                try:
                    await client.start_notify(
                        LIVE_CHAR, lambda _char, value: notifications.append(bytes(value).hex())
                    )
                    await asyncio.sleep(UNLOCK_DELAY)
                except BleakError as err:
                    LOGGER.debug("Subscribing to %s failed: %s", LIVE_CHAR, err)
            chars = SIGMA_READ_CHARS + (DEVICE_INFO_CHARS if read_device_info else [])
            for uuid in chars:
                if client.services.get_characteristic(uuid) is None:
                    continue
                try:
                    raw[uuid] = bytes(await client.read_gatt_char(uuid))
                except BleakError as err:
                    if paired or not _is_auth_error(err):
                        LOGGER.debug("Reading %s failed: %s", uuid, err)
                        continue
                    # The bike wants an encrypted link: pair once, then try again.
                    LOGGER.info("Bike %s asks for pairing, pairing now", ble_device.address)
                    await client.pair()
                    paired = True
                    raw[uuid] = bytes(await client.read_gatt_char(uuid))
        finally:
            try:
                async with asyncio.timeout(5):
                    await client.disconnect()
            except (BleakError, TimeoutError):
                pass

    if not raw:
        raise BleakError("No characteristics could be read")
    data = parse(raw)
    data.notifications = notifications
    return data
