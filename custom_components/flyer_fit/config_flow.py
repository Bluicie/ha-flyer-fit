"""Config flow for Flyer FIT e-bikes."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS

from .const import DOMAIN
from .parser import FIT_SERVICE_UUID, SIGMA_SERVICE_UUID


def _is_fit_bike(info: BluetoothServiceInfoBleak) -> bool:
    uuids = {u.lower() for u in info.service_uuids}
    return SIGMA_SERVICE_UUID in uuids or FIT_SERVICE_UUID in uuids


def _title(info: BluetoothServiceInfoBleak) -> str:
    return f"Flyer {info.name or info.address}"


class FlyerFitConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add a bike found over Bluetooth."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery: BluetoothServiceInfoBleak | None = None
        self._discovered: dict[str, BluetoothServiceInfoBleak] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """A bike was discovered by Home Assistant's Bluetooth."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        if not _is_fit_bike(discovery_info):
            return self.async_abort(reason="not_supported")
        self._discovery = discovery_info
        self.context["title_placeholders"] = {"name": _title(discovery_info)}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask the user to confirm the discovered bike."""
        assert self._discovery is not None
        if user_input is not None:
            return self.async_create_entry(title=_title(self._discovery), data={})
        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": _title(self._discovery)},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick a bike from the ones currently heard."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=_title(self._discovered[address]), data={}
            )

        configured = self._async_current_ids(include_ignore=False)
        for info in async_discovered_service_info(self.hass, connectable=True):
            if info.address in configured or not _is_fit_bike(info):
                continue
            self._discovered[info.address] = info
        if not self._discovered:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(
                        {
                            address: f"{_title(info)} ({address})"
                            for address, info in self._discovered.items()
                        }
                    )
                }
            ),
        )
