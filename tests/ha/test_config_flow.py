"""Config flow tests (need pytest-homeassistant-custom-component)."""

from unittest.mock import patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from bleak.backends.device import BLEDevice  # noqa: E402
from bleak.backends.scanner import AdvertisementData  # noqa: E402

from custom_components.flyer_fit.const import DOMAIN  # noqa: E402
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak  # noqa: E402
from homeassistant.config_entries import SOURCE_BLUETOOTH, SOURCE_USER  # noqa: E402
from homeassistant.data_entry_flow import FlowResultType  # noqa: E402

ADDRESS = "AA:BB:CC:DD:EE:FF"
NAME = "TESTSERIAL0000001"


def _info(uuids: list[str]) -> BluetoothServiceInfoBleak:
    return BluetoothServiceInfoBleak(
        name=NAME,
        address=ADDRESS,
        rssi=-60,
        manufacturer_data={},
        service_data={},
        service_uuids=uuids,
        source="local",
        device=BLEDevice(ADDRESS, NAME, {}),
        advertisement=AdvertisementData(
            local_name=NAME,
            manufacturer_data={},
            service_data={},
            service_uuids=uuids,
            tx_power=None,
            rssi=-60,
            platform_data=(),
        ),
        connectable=True,
        time=0,
        tx_power=None,
    )


BIKE = ["0000fd6d-0000-1000-8000-00805f9b34fb"]


@pytest.fixture(autouse=True)
def _custom(enable_custom_integrations, mock_bluetooth_adapters, mock_bleak_scanner_start):
    yield


@pytest.fixture(autouse=True)
def _no_setup():
    with patch("custom_components.flyer_fit.async_setup_entry", return_value=True):
        yield


async def test_bluetooth_discovery(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=_info(BIKE)
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Flyer TESTSERIAL0000001"
    assert result["result"].unique_id == ADDRESS


async def test_bluetooth_not_a_bike(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_BLUETOOTH},
        data=_info(["0000180f-0000-1000-8000-00805f9b34fb"]),
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_supported"


async def test_user_flow(hass):
    with patch(
        "custom_components.flyer_fit.config_flow.async_discovered_service_info",
        return_value=[_info(BIKE)],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"address": ADDRESS}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == ADDRESS


async def test_user_flow_no_bikes(hass):
    with patch(
        "custom_components.flyer_fit.config_flow.async_discovered_service_info",
        return_value=[],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"
