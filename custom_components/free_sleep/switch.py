"""Switch platform for Free Sleep."""

from __future__ import annotations

import logging
from typing import Any

from datetime import datetime, timedelta

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

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
        entities.append(FreeSleepAlarmDisableTonightSwitch(coordinator, entry, side))

    entities.append(FreeSleepPrimeDailySwitch(coordinator, entry))
    entities.append(FreeSleepBiometricsSwitch(coordinator, entry))
    entities.append(FreeSleepRebootDailySwitch(coordinator, entry))

    for side in SIDES:
        entities.append(FreeSleepTempScheduleDisableTonightSwitch(coordinator, entry, side))

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
        current = self.coordinator.data.today_alarm(self._side)
        await self.coordinator.api.set_alarm(self._side, day, {"enabled": True}, current)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        day = self.coordinator.data._today_key()
        current = self.coordinator.data.today_alarm(self._side)
        await self.coordinator.api.set_alarm(self._side, day, {"enabled": False}, current)
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


class FreeSleepAlarmDisableTonightSwitch(
    CoordinatorEntity[FreeSleepCoordinator], SwitchEntity
):
    """Switch to temporarily disable the alarm for tonight.

    Mirrors the web app's "Disable for tonight" button.  When turned on the
    alarm that would fire next (using noon-crossover logic) is skipped.  The
    override auto-expires 2 minutes after the scheduled alarm time.
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:alarm-off"

    def __init__(self, coordinator, entry, side) -> None:
        super().__init__(coordinator)
        self._side = side
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{side}_alarm_disable_tonight"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{side}")},
        )

    @property
    def name(self) -> str:
        return "Alarm Disable Tonight"

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.is_alarm_disabled_tonight(self._side)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Disable tonight's alarm by computing expiresAt from the schedule."""
        alarm = self.coordinator.data.tonight_alarm(self._side)
        alarm_time_str = alarm.get("time", "")
        if not alarm_time_str:
            _LOGGER.warning(
                "Cannot disable tonight's alarm for %s: no alarm time configured",
                self._side,
            )
            return

        # Parse the alarm time (HH:MM) and attach tonight's date
        now = dt_util.now()
        if now.hour >= 12:
            target_date = (now + timedelta(days=1)).date()
        else:
            target_date = now.date()

        try:
            parts = alarm_time_str.split(":")
            hour, minute = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            _LOGGER.error(
                "Cannot parse alarm time '%s' for %s", alarm_time_str, self._side
            )
            return

        # Build the alarm datetime in the HA timezone, then add 2 minutes
        tz = dt_util.get_default_time_zone()
        alarm_dt = datetime(
            target_date.year, target_date.month, target_date.day,
            hour, minute, 0, tzinfo=tz,
        )
        expires_at = alarm_dt + timedelta(minutes=2)

        await self.coordinator.api.set_settings(
            {
                self._side: {
                    "scheduleOverrides": {
                        "alarm": {
                            "disabled": True,
                            "timeOverride": "",
                            "expiresAt": expires_at.isoformat(),
                        }
                    }
                }
            }
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Re-enable tonight's alarm by clearing the override."""
        await self.coordinator.api.set_settings(
            {
                self._side: {
                    "scheduleOverrides": {
                        "alarm": {
                            "disabled": False,
                            "timeOverride": "",
                            "expiresAt": "",
                        }
                    }
                }
            }
        )
        await self.coordinator.async_request_refresh()


class FreeSleepRebootDailySwitch(CoordinatorEntity[FreeSleepCoordinator], SwitchEntity):
    """Switch to enable/disable daily automatic reboot."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:restart-clock"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_reboot_daily"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Eight Sleep Pod",
            manufacturer="Eight Sleep",
            model=coordinator.data.cover_version,
            sw_version=coordinator.data.free_sleep_version,
        )

    @property
    def name(self) -> str:
        return "Daily Reboot"

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.reboot_daily_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_reboot_daily(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_reboot_daily(False)
        await self.coordinator.async_request_refresh()


class FreeSleepTempScheduleDisableTonightSwitch(CoordinatorEntity[FreeSleepCoordinator], SwitchEntity):
    """Switch to temporarily disable temperature schedules for tonight."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:thermometer-off"

    def __init__(self, coordinator, entry, side) -> None:
        super().__init__(coordinator)
        self._side = side
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{side}_temp_schedule_disable_tonight"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{side}")},
        )

    @property
    def name(self) -> str:
        return "Temp Schedule Disable Tonight"

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.is_temp_schedule_disabled_tonight(self._side)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Disable temp schedules until noon tomorrow."""
        now = dt_util.now()
        if now.hour >= 12:
            target_date = (now + timedelta(days=1)).date()
        else:
            target_date = now.date()
        tz = dt_util.get_default_time_zone()
        expires_at = datetime(target_date.year, target_date.month, target_date.day, 12, 0, 0, tzinfo=tz)
        await self.coordinator.api.set_settings(
            {
                self._side: {
                    "scheduleOverrides": {
                        "temperatureSchedules": {
                            "disabled": True,
                            "expiresAt": expires_at.isoformat(),
                        }
                    }
                }
            }
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Re-enable temp schedules."""
        await self.coordinator.api.set_settings(
            {
                self._side: {
                    "scheduleOverrides": {
                        "temperatureSchedules": {
                            "disabled": False,
                            "expiresAt": "",
                        }
                    }
                }
            }
        )
        await self.coordinator.async_request_refresh()
