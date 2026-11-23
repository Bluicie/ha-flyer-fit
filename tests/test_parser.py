"""Tests for the parser, using values captured from a real Flyer bike.

The display showed: battery 37 %, range 36 km, odometer 1496 km, mode STD.
"""

import importlib.util
from pathlib import Path
import sys

# Load parser.py directly so the tests don't need Home Assistant installed.
_PATH = Path(__file__).parents[1] / "custom_components" / "flyer_fit" / "parser.py"
_spec = importlib.util.spec_from_file_location("flyer_fit_parser", _PATH)
parser = importlib.util.module_from_spec(_spec)
sys.modules["flyer_fit_parser"] = parser
_spec.loader.exec_module(parser)


def h(text: str) -> bytes:
    return bytes.fromhex(text.replace("-", ""))


CAPTURED = {
    parser.MANUFACTURER_CHAR: b"FLYER",
    parser.MODEL_CHAR: b"FIT E-Bike",
    parser.SERIAL_CHAR: b"TESTSERIAL0000001",
    parser.sigma_char(1): h("00-00-00-00-00-00-00-00-00-00"),
    parser.sigma_char(2): h("00-00-00-00-FF-FF-FF-FF-80-00"),
    parser.sigma_char(3): h("25-18-01-3E-8F-80-24-00-02-00-90-0C"),
    parser.sigma_char(4): h("FF-FF-00"),
    parser.sigma_char(5): h("D8-CF-16-00-44-D6-04-00-FF-FF-FF"),
    parser.sigma_char(6): h(
        "04-FF-FF-A0-8C-05-05-04-00-FF-FF-58-02-B6-03-01-15-4F-46-46-1E-45-43-4F-1E"
        "-53-54-44-1E-41-55-54-4F-1E-48-49-47-48"
    ),
    parser.sigma_char(7): h("02-00"),
    parser.sigma_char(8): h("00-64-00-64"),
}


def test_captured_values():
    data = parser.parse(CAPTURED)
    assert data.battery == 37
    assert data.range_km == 36
    assert data.odometer_km == 1495.0
    assert data.assist_modes == ["OFF", "ECO", "STD", "AUTO", "HIGH"]
    assert data.assist_mode == "STD"
    assert data.manufacturer == "FLYER"
    assert data.model == "FIT E-Bike"
    assert data.serial == "TESTSERIAL0000001"
    assert data.raw[parser.sigma_char(7)] == "0200"


def test_battery_electrics_not_charging():
    data = parser.parse(CAPTURED)
    # 0003 = 25 18013e 8f80 24 ...: 0x0118 mA, 0x8f3e mV
    assert data.current == 0.28
    assert data.voltage == 36.67
    assert data.power == 10.3
    assert data.charging is False


def test_battery_electrics_charging():
    """Captured while on the charger (display showed 63 %)."""
    raw = dict(CAPTURED)
    raw[parser.sigma_char(3)] = h("3f62e9fe9c80240003001014")
    raw[parser.sigma_char(4)] = h("ffff02")
    data = parser.parse(raw)
    assert data.battery == 63
    assert data.current == -5.79
    assert data.voltage == 40.19
    assert data.power < 0
    assert data.charging is True


def test_riding_time_and_speed():
    """0005 counted 12 s up in 12 s of pedalling; display showed about 14 km/h."""
    data = parser.parse(CAPTURED)
    assert data.riding_time_h == round(316996 / 3600, 2)
    raw = dict(CAPTURED)
    raw[parser.sigma_char(1)] = h("8a000a00000000000022")
    assert parser.parse(raw).speed_kmh == 13.8


def test_empty_input():
    data = parser.parse({})
    assert data.battery is None
    assert data.range_km is None
    assert data.odometer_km is None
    assert data.assist_mode is None
    assert data.assist_modes == []


def test_scrambled_unpaired_reading_is_ignored():
    """Captured by Home Assistant without pairing, while the bike was charging."""
    data = parser.parse(
        {
            parser.MODEL_CHAR: b"FIT E-Bike",
            parser.sigma_char(1): h("5f295e694071651fa57f"),
            parser.sigma_char(3): h("f300580b941dc3abf10e1145"),
            parser.sigma_char(5): h("8040f8fe8d7bffc4748a6b"),
            parser.sigma_char(6): b"",
            parser.sigma_char(7): h("4542"),
            parser.sigma_char(8): h("7dff0023"),
        }
    )
    assert data.model == "FIT E-Bike"
    assert data.battery is None
    assert data.range_km is None
    assert data.odometer_km is None
    assert data.assist_mode is None
    assert parser.sigma_char(3) in data.raw


def test_unknown_values_are_none():
    data = parser.parse(
        {
            parser.sigma_char(3): h("FF-00-00-00-00-00-FF"),
            parser.sigma_char(5): h("FF-FF-FF-FF"),
            parser.sigma_char(6): CAPTURED[parser.sigma_char(6)],
            parser.sigma_char(7): h("09"),
        }
    )
    assert data.battery is None
    assert data.range_km is None
    assert data.odometer_km is None
    assert data.assist_mode is None


def test_mode_index_out_of_range():
    raw = dict(CAPTURED)
    raw[parser.sigma_char(7)] = h("05")
    assert parser.parse(raw).assist_mode is None
