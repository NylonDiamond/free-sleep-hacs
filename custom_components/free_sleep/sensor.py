"""Sensor platform for Free Sleep."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTime
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
        FreeSleepWebAppUrlSensor(coordinator, entry, pod_device),
    ]

    for side in SIDES:
        side_device = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{side}")},
        )
        entities.append(
            FreeSleepCurrentTempSensor(coordinator, entry, side, side_device)
        )
        # Vitals sensors
        entities.append(
            FreeSleepVitalsSensor(
                coordinator, entry, side, side_device,
                "avgHeartRate", "Avg Heart Rate", "mdi:heart-pulse", "bpm",
            )
        )
        entities.append(
            FreeSleepVitalsSensor(
                coordinator, entry, side, side_device,
                "minHeartRate", "Min Heart Rate", "mdi:heart-minus", "bpm",
            )
        )
        entities.append(
            FreeSleepVitalsSensor(
                coordinator, entry, side, side_device,
                "maxHeartRate", "Max Heart Rate", "mdi:heart-plus", "bpm",
            )
        )
        entities.append(
            FreeSleepVitalsSensor(
                coordinator, entry, side, side_device,
                "avgHRV", "Avg HRV", "mdi:heart-flash", "ms",
            )
        )
        entities.append(
            FreeSleepVitalsSensor(
                coordinator, entry, side, side_device,
                "avgBreathingRate", "Avg Breathing Rate", "mdi:lungs", "br/min",
            )
        )
        # Sleep sensors
        entities.append(
            FreeSleepSleepDurationSensor(coordinator, entry, side, side_device)
        )
        entities.append(
            FreeSleepTimesExitedBedSensor(coordinator, entry, side, side_device)
        )
        entities.append(
            FreeSleepTimeRemainingSensor(coordinator, entry, side, side_device)
        )
        entities.append(
            FreeSleepNextAlarmSensor(coordinator, entry, side, side_device)
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


class FreeSleepWebAppUrlSensor(
    CoordinatorEntity[FreeSleepCoordinator], SensorEntity
):
    """Web app URL sensor - shows the free-sleep web interface URL."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:web"

    def __init__(self, coordinator, entry, device_info) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_web_app_url"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Web App URL"

    @property
    def native_value(self) -> str:
        return self.coordinator.api.base_url


class FreeSleepCurrentTempSensor(
    CoordinatorEntity[FreeSleepCoordinator], SensorEntity
):
    """Current temperature sensor for a side."""

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


class FreeSleepVitalsSensor(
    CoordinatorEntity[FreeSleepCoordinator], SensorEntity
):
    """Generic vitals sensor (heart rate, HRV, breathing rate)."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator, entry, side, device_info,
        key: str, display_name: str, icon: str, unit: str,
    ) -> None:
        super().__init__(coordinator)
        self._side = side
        self._key = key
        self._display_name = display_name
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = f"{entry.entry_id}_{side}_{key}"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return self._display_name

    @property
    def native_value(self) -> int | None:
        val = self.coordinator.data.side_vitals_summary(self._side).get(self._key)
        if val is None or val == 0:
            return None
        return val


class FreeSleepSleepDurationSensor(
    CoordinatorEntity[FreeSleepCoordinator], SensorEntity
):
    """Last sleep duration in hours."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:bed-clock"
    _attr_native_unit_of_measurement = "h"

    def __init__(self, coordinator, entry, side, device_info) -> None:
        super().__init__(coordinator)
        self._side = side
        self._attr_unique_id = f"{entry.entry_id}_{side}_sleep_duration"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Last Sleep Duration"

    @property
    def native_value(self) -> float | None:
        record = self.coordinator.data.side_last_sleep(self._side)
        if not record:
            return None
        seconds = record.get("sleep_period_seconds", 0)
        if seconds <= 0:
            return None
        return round(seconds / 3600, 1)


class FreeSleepTimesExitedBedSensor(
    CoordinatorEntity[FreeSleepCoordinator], SensorEntity
):
    """Number of times exited bed during last sleep."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:bed-empty"

    def __init__(self, coordinator, entry, side, device_info) -> None:
        super().__init__(coordinator)
        self._side = side
        self._attr_unique_id = f"{entry.entry_id}_{side}_times_exited_bed"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Times Exited Bed"

    @property
    def native_value(self) -> int | None:
        record = self.coordinator.data.side_last_sleep(self._side)
        if not record:
            return None
        return record.get("times_exited_bed")


class FreeSleepTimeRemainingSensor(
    CoordinatorEntity[FreeSleepCoordinator], SensorEntity
):
    """Seconds remaining until side auto-shuts off."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator, entry, side, device_info) -> None:
        super().__init__(coordinator)
        self._side = side
        self._attr_unique_id = f"{entry.entry_id}_{side}_time_remaining"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Time Remaining"

    @property
    def native_value(self) -> int:
        return self.coordinator.data.seconds_remaining(self._side)


class FreeSleepNextAlarmSensor(
    CoordinatorEntity[FreeSleepCoordinator], SensorEntity
):
    """Next alarm datetime (timestamp sensor)."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:alarm"

    def __init__(self, coordinator, entry, side, device_info) -> None:
        super().__init__(coordinator)
        self._side = side
        self._attr_unique_id = f"{entry.entry_id}_{side}_next_alarm"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Next Alarm"

    @property
    def native_value(self):
        return self.coordinator.data.next_alarm_datetime(self._side)
