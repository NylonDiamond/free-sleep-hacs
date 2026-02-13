"""Button platform for Free Sleep."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
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
    """Set up Free Sleep button entities."""
    coordinator: FreeSleepCoordinator = entry.runtime_data
    pod_device = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Eight Sleep Pod",
        manufacturer="Eight Sleep",
        model=coordinator.data.cover_version,
        sw_version=coordinator.data.free_sleep_version,
    )

    async_add_entities([
        FreeSleepPrimeButton(coordinator, entry, pod_device),
        FreeSleepRebootButton(coordinator, entry, pod_device),
        FreeSleepUpdateButton(coordinator, entry, pod_device),
    ])


class FreeSleepPrimeButton(
    CoordinatorEntity[FreeSleepCoordinator], ButtonEntity
):
    """Button to start priming."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:water-pump"

    def __init__(self, coordinator, entry, device_info) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_prime"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Prime Pod"

    async def async_press(self) -> None:
        """Press the button."""
        await self.coordinator.api.start_prime()
        await self.coordinator.async_request_refresh()


class FreeSleepRebootButton(
    CoordinatorEntity[FreeSleepCoordinator], ButtonEntity
):
    """Button to reboot the pod."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:restart"

    def __init__(self, coordinator, entry, device_info) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_reboot"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Reboot"

    async def async_press(self) -> None:
        """Press the button."""
        await self.coordinator.api.reboot()


class FreeSleepUpdateButton(
    CoordinatorEntity[FreeSleepCoordinator], ButtonEntity
):
    """Button to trigger a software update."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:update"

    def __init__(self, coordinator, entry, device_info) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_update"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Update Free Sleep"

    async def async_press(self) -> None:
        """Press the button."""
        await self.coordinator.api.update()
