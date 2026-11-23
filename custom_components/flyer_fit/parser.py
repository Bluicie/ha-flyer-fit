"""Parse the values a FIT 2.0 e-bike exposes over Bluetooth.

Pure Python, no Home Assistant imports, so it can be tested on its own.

The bike's display (made by Sigma Elektro) exposes a GATT service 0xFD6D with
characteristics ``0000000X-abab-4499-b9d7-d0efc0d06477``. The meanings below were
checked against the display of a Flyer bike:

* ``0003`` byte 0: battery state of charge in %; bytes 1-2: battery current in mA
  (int16, negative while charging); bytes 3-4: battery voltage in mV (uint16);
  byte 6: remaining range in km for the current assist mode (frozen while charging)
* ``0004`` byte 2: 0x02 while the charger is connected
* ``0001`` bytes 0-1: live speed in 0.1 km/h (notifies about twice a second)
* ``0005`` bytes 0-3: odometer in metres (little-endian uint32); bytes 4-7: total
  riding time in seconds (counts only while the wheel turns)
* ``0006``: settings block; ends with a length byte and the assist mode names,
  separated by 0x1E (for example ``OFF ECO STD AUTO HIGH``)
* ``0007`` byte 0: index of the current assist mode in that list
"""

from __future__ import annotations

from dataclasses import dataclass, field

SIGMA_SERVICE_UUID = "0000fd6d-0000-1000-8000-00805f9b34fb"
FIT_SERVICE_UUID = "5e8597aa-69d9-11ea-bc55-0242ac130003"

MANUFACTURER_CHAR = "00002a29-0000-1000-8000-00805f9b34fb"
MODEL_CHAR = "00002a24-0000-1000-8000-00805f9b34fb"
SERIAL_CHAR = "00002a25-0000-1000-8000-00805f9b34fb"


def sigma_char(number: int) -> str:
    """Return the UUID of Sigma characteristic ``number`` (1-14)."""
    return f"{number:08x}-abab-4499-b9d7-d0efc0d06477"


LIVE_CHAR = sigma_char(0x01)
BATTERY_CHAR = sigma_char(0x03)
STATUS_CHAR = sigma_char(0x04)
ODOMETER_CHAR = sigma_char(0x05)
SETTINGS_CHAR = sigma_char(0x06)
ASSIST_MODE_CHAR = sigma_char(0x07)

# Every readable characteristic of the Sigma service. All are read on each poll so
# that the diagnostics download contains the raw data needed to decode more fields.
SIGMA_READ_CHARS = [sigma_char(n) for n in (1, 2, 3, 4, 5, 6, 7, 8, 9, 0x0B, 0x0C, 0x0D)]
DEVICE_INFO_CHARS = [MANUFACTURER_CHAR, MODEL_CHAR, SERIAL_CHAR]

MODE_SEPARATOR = 0x1E


@dataclass
class FitData:
    """Values read from the bike in one poll."""

    battery: int | None = None
    range_km: int | None = None
    voltage: float | None = None
    current: float | None = None
    power: float | None = None
    charging: bool | None = None
    odometer_km: float | None = None
    riding_time_h: float | None = None
    speed_kmh: float | None = None
    assist_mode: str | None = None
    assist_modes: list[str] = field(default_factory=list)
    manufacturer: str | None = None
    model: str | None = None
    serial: str | None = None
    raw: dict[str, str] = field(default_factory=dict)
    # Live notifications from characteristic 0001 received during the read (hex).
    notifications: list[str] = field(default_factory=list)


def _text(value: bytes | None) -> str | None:
    if not value:
        return None
    text = value.decode("utf-8", "replace").strip("\x00").strip()
    return text or None


def parse_assist_modes(settings: bytes | None) -> list[str]:
    """Find the assist mode names at the end of the settings block.

    The names are preceded by a byte that holds their total length.
    """
    if not settings:
        return []
    for start in range(len(settings) - 1):
        length = settings[start]
        text = settings[start + 1 :]
        if length != len(text) or length == 0:
            continue
        if all(32 <= b < 127 or b == MODE_SEPARATOR for b in text):
            return [m for m in text.decode("ascii").split(chr(MODE_SEPARATOR)) if m]
    return []


def parse(raw: dict[str, bytes]) -> FitData:
    """Turn the raw characteristic values into a FitData."""
    data = FitData(raw={uuid: value.hex() for uuid, value in raw.items()})

    data.manufacturer = _text(raw.get(MANUFACTURER_CHAR))
    data.model = _text(raw.get(MODEL_CHAR))
    data.serial = _text(raw.get(SERIAL_CHAR))

    # Until a client subscribes to 0001 the bike returns scrambled values and an
    # empty settings block. The assist mode names are only present in a real
    # reading, so use them as the sign that the other values can be trusted.
    data.assist_modes = parse_assist_modes(raw.get(SETTINGS_CHAR))
    if not data.assist_modes:
        return data

    battery = raw.get(BATTERY_CHAR)
    if battery and len(battery) >= 1 and battery[0] <= 100:
        data.battery = battery[0]
    if battery and len(battery) >= 7 and battery[6] != 0xFF:
        data.range_km = battery[6]
    if battery and len(battery) >= 5:
        millivolts = int.from_bytes(battery[3:5], "little")
        milliamps = int.from_bytes(battery[1:3], "little", signed=True)
        if 0 < millivolts < 0xFFFF:
            data.voltage = round(millivolts / 1000, 2)
            data.current = round(milliamps / 1000, 2)
            data.power = round(millivolts * milliamps / 1_000_000, 1)

    status = raw.get(STATUS_CHAR)
    if status and len(status) >= 3:
        data.charging = status[2] == 0x02

    odometer = raw.get(ODOMETER_CHAR)
    if odometer and len(odometer) >= 4:
        metres = int.from_bytes(odometer[0:4], "little")
        if metres != 0xFFFFFFFF:
            data.odometer_km = round(metres / 1000, 1)
    if odometer and len(odometer) >= 8:
        seconds = int.from_bytes(odometer[4:8], "little")
        if seconds != 0xFFFFFFFF:
            data.riding_time_h = round(seconds / 3600, 2)

    live = raw.get(LIVE_CHAR)
    if live and len(live) >= 2:
        data.speed_kmh = int.from_bytes(live[0:2], "little") / 10

    mode = raw.get(ASSIST_MODE_CHAR)
    if mode and mode[0] < len(data.assist_modes):
        data.assist_mode = data.assist_modes[mode[0]]

    return data
