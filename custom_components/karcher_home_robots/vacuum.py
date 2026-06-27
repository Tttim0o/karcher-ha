"""Vacuum platform for Kärcher Home Robots."""
from __future__ import annotations

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumEntityFeature,
    VacuumActivity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN, KarcherDataCoordinator
from .karcher_api import KarcherDevice

FEATURES = (
    VacuumEntityFeature.START
    | VacuumEntityFeature.STOP
    | VacuumEntityFeature.PAUSE
    | VacuumEntityFeature.RETURN_HOME
    | VacuumEntityFeature.BATTERY
    | VacuumEntityFeature.STATE
)

STATE_MAP = {
    "cleaning": VacuumActivity.CLEANING,
    "paused": VacuumActivity.PAUSED,
    "returning": VacuumActivity.RETURNING,
    "docked": VacuumActivity.DOCKED,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: KarcherDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        KarcherVacuumEntity(coordinator, device)
        for device in (coordinator.data or [])
    ]
    async_add_entities(entities, True)


class KarcherVacuumEntity(CoordinatorEntity[KarcherDataCoordinator], StateVacuumEntity):
    _attr_supported_features = FEATURES
    _attr_has_entity_name = True
    _attr_name = None  # Use device name as entity name

    def __init__(self, coordinator: KarcherDataCoordinator, device: KarcherDevice) -> None:
        super().__init__(coordinator)
        self._device_id = device.device_id
        self._attr_unique_id = f"karcher_{device.device_id}"
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
    def activity(self) -> VacuumActivity | None:
        d = self._device
        if d is None:
            return None
        return STATE_MAP.get(d.state, VacuumActivity.DOCKED)

    @property
    def battery_level(self) -> int | None:
        d = self._device
        return d.battery if d else None

    @property
    def available(self) -> bool:
        d = self._device
        return d is not None and d.online

    async def async_start(self) -> None:
        await self.coordinator.api.start_cleaning(self._device_id)
        await self.coordinator.async_request_refresh()

    async def async_stop(self, **kwargs) -> None:
        await self.coordinator.api.stop_cleaning(self._device_id)
        await self.coordinator.async_request_refresh()

    async def async_pause(self) -> None:
        await self.coordinator.api.pause_cleaning(self._device_id)
        await self.coordinator.async_request_refresh()

    async def async_return_to_base(self, **kwargs) -> None:
        await self.coordinator.api.return_to_base(self._device_id)
        await self.coordinator.async_request_refresh()
