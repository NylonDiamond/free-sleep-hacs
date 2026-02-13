"""Select platform for Free Sleep."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FreeSleepCoordinator

_LOGGER = logging.getLogger(__name__)

SIDES = ["left", "right"]

GESTURES = ["doubleTap", "tripleTap", "quadTap"]
GESTURE_DISPLAY = {
    "doubleTap": "Double Tap",
    "tripleTap": "Triple Tap",
    "quadTap": "Quad Tap",
}

# Tap action options and their API payloads
TAP_OPTIONS = {
    "Decrease Temperature": {
        "type": "temperature",
        "change": "decrement",
        "amount": 1,
    },
    "Increase Temperature": {
        "type": "temperature",
        "change": "increment",
        "amount": 1,
    },
    "Dismiss Alarm": {
        "type": "alarm",
        "behavior": "dismiss",
        "snoozeDuration": 60,
        "inactiveAlarmBehavior": "power",
    },
    "Snooze Alarm": {
        "type": "alarm",
        "behavior": "snooze",
        "snoozeDuration": 60,
        "inactiveAlarmBehavior": "power",
    },
}

ALARM_VIBRATION_PATTERNS = ["double", "rise"]


def _tap_config_to_label(config: dict[str, Any]) -> str:
    """Convert a tap config dict to a human-readable label."""
    tap_type = config.get("type", "")
    if tap_type == "temperature":
        change = config.get("change", "")
        if change == "decrement":
            return "Decrease Temperature"
        return "Increase Temperature"
    if tap_type == "alarm":
        behavior = config.get("behavior", "")
        if behavior == "snooze":
            return "Snooze Alarm"
        return "Dismiss Alarm"
    return "Decrease Temperature"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Free Sleep select entities."""
    coordinator: FreeSleepCoordinator = entry.runtime_data
    entities: list[SelectEntity] = []

    for side in SIDES:
        side_device = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{side}")},
        )
        for gesture in GESTURES:
            entities.append(
                FreeSleepTapGestureSelect(
                    coordinator, entry, side, gesture, side_device
                )
            )
        entities.append(
            FreeSleepAlarmVibrationPatternSelect(
                coordinator, entry, side, side_device
            )
        )

    async_add_entities(entities)


class FreeSleepTapGestureSelect(
    CoordinatorEntity[FreeSleepCoordinator], SelectEntity
):
    """Select entity for tap gesture behavior."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:gesture-tap"
    _attr_options = list(TAP_OPTIONS.keys())

    def __init__(self, coordinator, entry, side, gesture, device_info) -> None:
        super().__init__(coordinator)
        self._side = side
        self._gesture = gesture
        self._attr_unique_id = f"{entry.entry_id}_{side}_{gesture}"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return f"{GESTURE_DISPLAY[self._gesture]} Action"

    @property
    def current_option(self) -> str | None:
        config = self.coordinator.data.tap_config(self._side, self._gesture)
        if not config:
            return None
        return _tap_config_to_label(config)

    async def async_select_option(self, option: str) -> None:
        payload = TAP_OPTIONS.get(option)
        if payload is None:
            return
        await self.coordinator.api.set_tap_config(
            self._side, self._gesture, payload
        )
        await self.coordinator.async_request_refresh()


class FreeSleepAlarmVibrationPatternSelect(
    CoordinatorEntity[FreeSleepCoordinator], SelectEntity
):
    """Select entity for alarm vibration pattern."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:sine-wave"
    _attr_options = ALARM_VIBRATION_PATTERNS

    def __init__(self, coordinator, entry, side, device_info) -> None:
        super().__init__(coordinator)
        self._side = side
        self._attr_unique_id = f"{entry.entry_id}_{side}_alarm_vibration_pattern"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Alarm Vibration Pattern"

    @property
    def current_option(self) -> str | None:
        return self.coordinator.data.today_alarm(self._side).get(
            "vibrationPattern", "rise"
        )

    async def async_select_option(self, option: str) -> None:
        day = self.coordinator.data._today_key()
        await self.coordinator.api.set_alarm(
            self._side, day, {"vibrationPattern": option}
        )
        await self.coordinator.async_request_refresh()
