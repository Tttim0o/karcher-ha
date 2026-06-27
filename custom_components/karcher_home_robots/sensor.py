"""Sensor platform for Kärcher Home Robots."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN, KarcherDataCoordinator
from .karcher_api import KarcherDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: KarcherDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        KarcherBatterySensor(coordinator, device)
        for device in (coordinator.data or [])
    ], True)


class KarcherBatterySensor(CoordinatorEntity[KarcherDataCoordinator], SensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_has_entity_name = True
    _attr_name = "Battery"

    def __init__(self, coordinator: KarcherDataCoordinator, device: KarcherDevice) -> None:
        super().__init__(coordinator)
        self._device_id = device.device_id
        self._attr_unique_id = f"karcher_{device.device_id}_battery"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.device_id)},
            name=device.name,
            manufacturer="Kärcher",
            model=device.model,
        )

    @property
    def _device(self) -> KarcherDevice | None:
        for d in (self.coordinator.data or []):
            if d.device_id == self._device_id:
                return d
        return None

    @property
    def native_value(self) -> int | None:
        d = self._device
        return d.battery if d else None

    @property
    def available(self) -> bool:
        return self._device is not None
