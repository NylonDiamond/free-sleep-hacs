"""Sensor platform for Free Sleep."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
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
    """Set up Free Sleep sensor entities."""
    coordinator: FreeSleepCoordinator = entry.runtime_data
    pod_device = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Eight Sleep Pod",
        manufacturer="Eight Sleep",
        model=coordinator.data.cover_version,
        sw_version=coordinator.data.free_sleep_version,
    )

    entities: list[SensorEntity] = [
        FreeSleepWaterLevelSensor(coordinator, entry, pod_device),
        FreeSleepWifiStrengthSensor(coordinator, entry, pod_device),
        FreeSleepCoverVersionSensor(coordinator, entry, pod_device),
        FreeSleepHubVersionSensor(coordinator, entry, pod_device),
        FreeSleepVersionSensor(coordinator, entry, pod_device),
    ]

    for side in SIDES:
        side_device = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{side}")},
        )
        entities.append(
            FreeSleepCurrentTempSensor(coordinator, entry, side, side_device)
        )

    async_add_entities(entities)


class FreeSleepWaterLevelSensor(
    CoordinatorEntity[FreeSleepCoordinator], SensorEntity
):
    """Water level sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:water"

    def __init__(self, coordinator, entry, device_info) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_water_level"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Water Level"

    @property
    def native_value(self) -> str:
        val = self.coordinator.data.water_level
        # The API returns "true" or "false" for water level (true = OK)
        if val == "true":
            return "OK"
        if val == "false":
            return "Low"
        return val


class FreeSleepWifiStrengthSensor(
    CoordinatorEntity[FreeSleepCoordinator], SensorEntity
):
    """WiFi signal strength sensor."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:wifi"

    def __init__(self, coordinator, entry, device_info) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_wifi_strength"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "WiFi Strength"

    @property
    def native_value(self) -> int:
        return self.coordinator.data.wifi_strength


class FreeSleepCoverVersionSensor(
    CoordinatorEntity[FreeSleepCoordinator], SensorEntity
):
    """Cover (mattress cover) version sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:information-outline"

    def __init__(self, coordinator, entry, device_info) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_cover_version"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Cover Version"

    @property
    def native_value(self) -> str:
        return self.coordinator.data.cover_version


class FreeSleepHubVersionSensor(
    CoordinatorEntity[FreeSleepCoordinator], SensorEntity
):
    """Hub version sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:information-outline"

    def __init__(self, coordinator, entry, device_info) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_hub_version"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Hub Version"

    @property
    def native_value(self) -> str:
        return self.coordinator.data.hub_version


class FreeSleepVersionSensor(
    CoordinatorEntity[FreeSleepCoordinator], SensorEntity
):
    """Free Sleep software version sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:tag"

    def __init__(self, coordinator, entry, device_info) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_free_sleep_version"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Free Sleep Version"

    @property
    def native_value(self) -> str:
        version = self.coordinator.data.free_sleep_version
        branch = self.coordinator.data.free_sleep_branch
        return f"{version} ({branch})"


class FreeSleepCurrentTempSensor(
    CoordinatorEntity[FreeSleepCoordinator], SensorEntity
):
    """Current temperature sensor for a side (useful as extra attribute)."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = "°F"
    _attr_icon = "mdi:thermometer"

    def __init__(self, coordinator, entry, side, device_info) -> None:
        super().__init__(coordinator)
        self._side = side
        self._attr_unique_id = f"{entry.entry_id}_{side}_current_temp"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Current Temperature"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.side_status(self._side).get("currentTemperatureF")
