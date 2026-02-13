"""Time platform for Free Sleep."""

from __future__ import annotations

import logging
from datetime import time as dt_time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FreeSleepCoordinator

_LOGGER = logging.getLogger(__name__)

SIDES = ["left", "right"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Free Sleep time entities."""
    coordinator: FreeSleepCoordinator = entry.runtime_data
    pod_device = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Eight Sleep Pod",
        manufacturer="Eight Sleep",
        model=coordinator.data.cover_version,
        sw_version=coordinator.data.free_sleep_version,
    )

    entities: list[TimeEntity] = [
        FreeSleepPrimeDailyTime(coordinator, entry, pod_device),
    ]

    for side in SIDES:
        side_device = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{side}")},
        )
        entities.append(
            FreeSleepAlarmTime(coordinator, entry, side, side_device)
        )

    async_add_entities(entities)


def _parse_time(time_str: str) -> dt_time | None:
    """Parse HH:MM string to time object."""
    try:
        parts = time_str.split(":")
        return dt_time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        return None


class FreeSleepPrimeDailyTime(
    CoordinatorEntity[FreeSleepCoordinator], TimeEntity
):
    """Time entity for the daily prime schedule."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator, entry, device_info) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_prime_daily_time"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Prime Pod Daily Time"

    @property
    def native_value(self) -> dt_time | None:
        return _parse_time(self.coordinator.data.prime_daily_time)

    async def async_set_value(self, value: dt_time) -> None:
        time_str = f"{value.hour:02d}:{value.minute:02d}"
        await self.coordinator.api.set_prime_daily_time(time_str)
        await self.coordinator.async_request_refresh()


class FreeSleepAlarmTime(
    CoordinatorEntity[FreeSleepCoordinator], TimeEntity
):
    """Alarm time for today for a side."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:alarm"

    def __init__(self, coordinator, entry, side, device_info) -> None:
        super().__init__(coordinator)
        self._side = side
        self._attr_unique_id = f"{entry.entry_id}_{side}_alarm_time"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Alarm Time"

    @property
    def native_value(self) -> dt_time | None:
        time_str = self.coordinator.data.today_alarm(self._side).get("time", "09:00")
        return _parse_time(time_str)

    async def async_set_value(self, value: dt_time) -> None:
        time_str = f"{value.hour:02d}:{value.minute:02d}"
        day = self.coordinator.data._today_key()
        await self.coordinator.api.set_alarm(self._side, day, {"time": time_str})
        await self.coordinator.async_request_refresh()
