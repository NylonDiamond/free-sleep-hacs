"""Switch platform for Free Sleep."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    """Set up Free Sleep switch entities."""
    coordinator: FreeSleepCoordinator = entry.runtime_data
    entities: list[SwitchEntity] = []

    for side in SIDES:
        entities.append(FreeSleepAwayModeSwitch(coordinator, entry, side))
        entities.append(FreeSleepAlarmEnabledSwitch(coordinator, entry, side))

    entities.append(FreeSleepPrimeDailySwitch(coordinator, entry))
    entities.append(FreeSleepBiometricsSwitch(coordinator, entry))

    async_add_entities(entities)


class FreeSleepAwayModeSwitch(CoordinatorEntity[FreeSleepCoordinator], SwitchEntity):
    """Switch for away mode on one side."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:bag-suitcase"

    def __init__(
        self,
        coordinator: FreeSleepCoordinator,
        entry: ConfigEntry,
        side: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._side = side
        self._attr_unique_id = f"{entry.entry_id}_{side}_away_mode"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{side}")},
        )

    @property
    def name(self) -> str:
        return "Away Mode"

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.away_mode(self._side)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_away_mode(self._side, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_away_mode(self._side, False)
        await self.coordinator.async_request_refresh()


class FreeSleepAlarmEnabledSwitch(
    CoordinatorEntity[FreeSleepCoordinator], SwitchEntity
):
    """Switch to enable/disable today's alarm for a side."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:alarm"

    def __init__(self, coordinator, entry, side) -> None:
        super().__init__(coordinator)
        self._side = side
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{side}_alarm_enabled"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{side}")},
        )

    @property
    def name(self) -> str:
        return "Alarm Enabled"

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.today_alarm(self._side).get("enabled", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        day = self.coordinator.data._today_key()
        await self.coordinator.api.set_alarm(self._side, day, {"enabled": True})
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        day = self.coordinator.data._today_key()
        await self.coordinator.api.set_alarm(self._side, day, {"enabled": False})
        await self.coordinator.async_request_refresh()


class FreeSleepPrimeDailySwitch(CoordinatorEntity[FreeSleepCoordinator], SwitchEntity):
    """Switch for daily pod priming."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:water-sync"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_prime_daily"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Eight Sleep Pod",
            manufacturer="Eight Sleep",
            model=coordinator.data.cover_version,
            sw_version=coordinator.data.free_sleep_version,
        )

    @property
    def name(self) -> str:
        return "Prime Pod Daily"

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.prime_daily_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_prime_daily(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_prime_daily(False)
        await self.coordinator.async_request_refresh()


class FreeSleepBiometricsSwitch(
    CoordinatorEntity[FreeSleepCoordinator], SwitchEntity
):
    """Switch to enable/disable biometrics collection."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:heart-pulse"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_biometrics_enabled"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Eight Sleep Pod",
            manufacturer="Eight Sleep",
            model=coordinator.data.cover_version,
            sw_version=coordinator.data.free_sleep_version,
        )

    @property
    def name(self) -> str:
        return "Biometrics"

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.biometrics_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_biometrics_enabled(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_biometrics_enabled(False)
        await self.coordinator.async_request_refresh()
