"""The Free Sleep integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FreeSleepApi
from .const import CONF_HOST, CONF_PORT, DEFAULT_PORT, DOMAIN, PLATFORMS
from .coordinator import FreeSleepCoordinator

_LOGGER = logging.getLogger(__name__)

type FreeSleepConfigEntry = ConfigEntry[FreeSleepCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: FreeSleepConfigEntry) -> bool:
    """Set up Free Sleep from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)

    session = async_get_clientsession(hass)
    api = FreeSleepApi(host, port, session)

    coordinator = FreeSleepCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: FreeSleepConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
