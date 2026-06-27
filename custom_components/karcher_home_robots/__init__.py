"""Kärcher Home Robots integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_REGION, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .karcher_api import KarcherApi, KarcherAuthError, KarcherApiError, KarcherDevice

_LOGGER = logging.getLogger(__name__)
DOMAIN = "karcher_home_robots"
PLATFORMS = [Platform.VACUUM, Platform.SENSOR]
SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api = KarcherApi(region=entry.data.get(CONF_REGION, "eu"))
    try:
        await api.login(entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
    except KarcherAuthError as err:
        await api.close()
        raise ConfigEntryAuthFailed(err) from err
    except Exception as err:
        await api.close()
        raise ConfigEntryNotReady(err) from err

    coordinator = KarcherDataCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        coordinator: KarcherDataCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.api.close()
    return unloaded


class KarcherDataCoordinator(DataUpdateCoordinator[list[KarcherDevice]]):
    """Polls the Kärcher API for device state."""

    def __init__(self, hass: HomeAssistant, api: KarcherApi) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.api = api

    async def _async_update_data(self) -> list[KarcherDevice]:
        try:
            return await self.api.get_devices()
        except KarcherAuthError as err:
            raise ConfigEntryAuthFailed(err) from err
        except KarcherApiError as err:
            raise UpdateFailed(err) from err
