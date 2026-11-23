"""Sensors for Flyer FIT e-bikes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfLength,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DEFAULT_ASSIST_MODES
from .coordinator import FlyerFitConfigEntry, FlyerFitCoordinator
from .entity import FlyerFitEntity
from .parser import FitData


@dataclass(frozen=True, kw_only=True)
class FlyerFitSensorDescription(SensorEntityDescription):
    """Describes a bike sensor."""

    value_fn: Callable[[FitData], float | int | str | None]


def _assist_mode(data: FitData) -> str | None:
    mode = (data.assist_mode or "").lower()
    return mode if mode in DEFAULT_ASSIST_MODES else None


SENSORS: tuple[FlyerFitSensorDescription, ...] = (
    FlyerFitSensorDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.battery,
    ),
    FlyerFitSensorDescription(
        key="range",
        translation_key="range",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.range_km,
    ),
    FlyerFitSensorDescription(
        key="voltage",
        translation_key="battery_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.voltage,
    ),
    FlyerFitSensorDescription(
        key="current",
        translation_key="battery_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.current,
    ),
    FlyerFitSensorDescription(
        key="power",
        translation_key="battery_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d: d.power,
    ),
    FlyerFitSensorDescription(
        key="odometer",
        translation_key="odometer",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=lambda d: d.odometer_km,
    ),
    FlyerFitSensorDescription(
        key="riding_time",
        translation_key="riding_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=lambda d: d.riding_time_h,
    ),
    FlyerFitSensorDescription(
        key="assist_mode",
        translation_key="assist_mode",
        device_class=SensorDeviceClass.ENUM,
        options=DEFAULT_ASSIST_MODES,
        value_fn=_assist_mode,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FlyerFitConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the bike's sensors."""
    coordinator = entry.runtime_data
    async_add_entities(FlyerFitSensor(coordinator, d) for d in SENSORS)


class FlyerFitSensor(FlyerFitEntity, RestoreSensor):
    """A value read from the bike. Keeps its last value while the bike is off."""

    entity_description: FlyerFitSensorDescription

    def __init__(
        self, coordinator: FlyerFitCoordinator, description: FlyerFitSensorDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._restored: float | int | str | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_sensor_data()) is not None:
            self._restored = last.native_value

    @property
    def native_value(self) -> float | int | str | None:
        value = None
        if self.coordinator.data is not None:
            value = self.entity_description.value_fn(self.coordinator.data)
        return value if value is not None else self._restored
