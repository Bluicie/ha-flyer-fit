"""Binary sensors for Flyer FIT e-bikes."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import FlyerFitConfigEntry
from .entity import FlyerFitEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FlyerFitConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the bike's binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [FlyerFitPoweredOn(coordinator, "powered_on"), FlyerFitCharging(coordinator, "charging")]
    )


class FlyerFitPoweredOn(FlyerFitEntity, BinarySensorEntity):
    """On while the bike's system is switched on (it then advertises)."""

    _attr_device_class = BinarySensorDeviceClass.POWER
    _attr_translation_key = "powered_on"

    @property
    def is_on(self) -> bool:
        return self.coordinator.powered_on


class FlyerFitCharging(FlyerFitEntity, BinarySensorEntity):
    """On while the charger is connected.

    The bike switches its display on when the charger is plugged in, so a bike
    that is off is not charging.
    """

    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.powered_on:
            return False
        return self.coordinator.data.charging if self.coordinator.data else None
