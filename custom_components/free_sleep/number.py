"""Number platform for Free Sleep."""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FreeSleepCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Free Sleep number entities."""
    coordinator: FreeSleepCoordinator = entry.runtime_data
    pod_device = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Eight Sleep Pod",
        manufacturer="Eight Sleep",
        model=coordinator.data.cover_version,
        sw_version=coordinator.data.free_sleep_version,
    )

    async_add_entities([
        FreeSleepLedBrightness(coordinator, entry, pod_device),
    ])


class FreeSleepLedBrightness(
    CoordinatorEntity[FreeSleepCoordinator], NumberEntity
):
    """LED brightness control."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:brightness-6"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator, entry, device_info) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_led_brightness"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "LED Brightness"

    @property
    def native_value(self) -> float:
        return self.coordinator.data.led_brightness

    async def async_set_native_value(self, value: float) -> None:
        """Set LED brightness."""
        await self.coordinator.api.set_led_brightness(int(value))
        await self.coordinator.async_request_refresh()
