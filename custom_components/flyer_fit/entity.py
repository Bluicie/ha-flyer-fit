"""Base entity for Flyer FIT."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import FlyerFitCoordinator


class FlyerFitEntity(CoordinatorEntity[FlyerFitCoordinator]):
    """An entity belonging to one bike."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: FlyerFitCoordinator, key: str) -> None:
        super().__init__(coordinator)
        data = coordinator.data
        self._attr_unique_id = f"{coordinator.address}_{key}"
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, coordinator.address)},
            name=coordinator.config_entry.title,
            manufacturer=(data.manufacturer if data else None) or "Flyer",
            model=(data.model if data else None) or "FIT E-Bike",
            serial_number=data.serial if data else None,
        )
