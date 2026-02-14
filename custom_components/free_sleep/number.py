"""Number platform for Free Sleep."""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MIN_TEMP_F, MAX_TEMP_F
from .coordinator import FreeSleepCoordinator

_LOGGER = logging.getLogger(__name__)

SIDES = ["left", "right"]


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

    entities: list[NumberEntity] = [
        FreeSleepLedBrightness(coordinator, entry, pod_device),
    ]

    for side in SIDES:
        side_device = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{side}")},
        )
        entities.append(
            FreeSleepAlarmVibrationIntensity(coordinator, entry, side, side_device)
        )
        entities.append(
            FreeSleepAlarmTemperature(coordinator, entry, side, side_device)
        )
        entities.append(
            FreeSleepAlarmDuration(coordinator, entry, side, side_device)
        )
        entities.append(
            FreeSleepGain(coordinator, entry, side, side_device)
        )

    async_add_entities(entities)


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
        await self.coordinator.api.set_led_brightness(int(value))
        await self.coordinator.async_request_refresh()


class FreeSleepAlarmVibrationIntensity(
    CoordinatorEntity[FreeSleepCoordinator], NumberEntity
):
    """Alarm vibration intensity (1-100)."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:vibrate"
    _attr_native_min_value = 1
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator, entry, side, device_info) -> None:
        super().__init__(coordinator)
        self._side = side
        self._attr_unique_id = f"{entry.entry_id}_{side}_alarm_vibration_intensity"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Alarm Vibration Intensity"

    @property
    def native_value(self) -> float:
        return self.coordinator.data.today_alarm(self._side).get(
            "vibrationIntensity", 100
        )

    async def async_set_native_value(self, value: float) -> None:
        day = self.coordinator.data._today_key()
        current = self.coordinator.data.today_alarm(self._side)
        await self.coordinator.api.set_alarm(
            self._side, day, {"vibrationIntensity": int(value)}, current
        )
        await self.coordinator.async_request_refresh()


class FreeSleepAlarmTemperature(
    CoordinatorEntity[FreeSleepCoordinator], NumberEntity
):
    """Alarm temperature setting (55-110°F)."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:thermometer-alert"
    _attr_native_min_value = MIN_TEMP_F
    _attr_native_max_value = MAX_TEMP_F
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = "°F"

    def __init__(self, coordinator, entry, side, device_info) -> None:
        super().__init__(coordinator)
        self._side = side
        self._attr_unique_id = f"{entry.entry_id}_{side}_alarm_temperature"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Alarm Temperature"

    @property
    def native_value(self) -> float:
        return self.coordinator.data.today_alarm(self._side).get(
            "alarmTemperature", 82
        )

    async def async_set_native_value(self, value: float) -> None:
        day = self.coordinator.data._today_key()
        current = self.coordinator.data.today_alarm(self._side)
        await self.coordinator.api.set_alarm(
            self._side, day, {"alarmTemperature": int(value)}, current
        )
        await self.coordinator.async_request_refresh()


class FreeSleepAlarmDuration(
    CoordinatorEntity[FreeSleepCoordinator], NumberEntity
):
    """Alarm vibration duration in minutes (0-180)."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:timer-outline"
    _attr_native_min_value = 0
    _attr_native_max_value = 180
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = "min"

    def __init__(self, coordinator, entry, side, device_info) -> None:
        super().__init__(coordinator)
        self._side = side
        self._attr_unique_id = f"{entry.entry_id}_{side}_alarm_duration"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Alarm Duration"

    @property
    def native_value(self) -> float:
        return self.coordinator.data.today_alarm(self._side).get("duration", 10)

    async def async_set_native_value(self, value: float) -> None:
        day = self.coordinator.data._today_key()
        current = self.coordinator.data.today_alarm(self._side)
        await self.coordinator.api.set_alarm(
            self._side, day, {"duration": int(value)}, current
        )
        await self.coordinator.async_request_refresh()


class FreeSleepGain(CoordinatorEntity[FreeSleepCoordinator], NumberEntity):
    """Heating/cooling gain (power multiplier) for a side."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:lightning-bolt"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator, entry, side, device_info) -> None:
        super().__init__(coordinator)
        self._side = side
        self._attr_unique_id = f"{entry.entry_id}_{side}_gain"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Gain"

    @property
    def native_value(self) -> float:
        return self.coordinator.data.gain(self._side)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.api.set_gain(self._side, int(value))
        await self.coordinator.async_request_refresh()
