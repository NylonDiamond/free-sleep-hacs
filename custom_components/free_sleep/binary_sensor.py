"""Binary sensor platform for Free Sleep."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    """Set up Free Sleep binary sensor entities."""
    coordinator: FreeSleepCoordinator = entry.runtime_data
    pod_device = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Eight Sleep Pod",
        manufacturer="Eight Sleep",
        model=coordinator.data.cover_version,
        sw_version=coordinator.data.free_sleep_version,
    )

    entities: list[BinarySensorEntity] = [
        FreeSleepPrimingSensor(coordinator, entry, pod_device),
        FreeSleepServerHealthSensor(coordinator, entry, pod_device),
    ]

    for side in SIDES:
        side_device = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{side}")},
        )
        entities.append(
            FreeSleepPresenceSensor(coordinator, entry, side, side_device)
        )
        entities.append(
            FreeSleepAlarmVibratingSensor(coordinator, entry, side, side_device)
        )
        entities.append(
            FreeSleepSideOnSensor(coordinator, entry, side, side_device)
        )

    async_add_entities(entities)


class FreeSleepPresenceSensor(
    CoordinatorEntity[FreeSleepCoordinator], BinarySensorEntity
):
    """Bed presence sensor for a side."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY
    _attr_icon = "mdi:bed"

    def __init__(self, coordinator, entry, side, device_info) -> None:
        super().__init__(coordinator)
        self._side = side
        self._attr_unique_id = f"{entry.entry_id}_{side}_presence"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Bed Presence"

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.is_present(self._side)


class FreeSleepAlarmVibratingSensor(
    CoordinatorEntity[FreeSleepCoordinator], BinarySensorEntity
):
    """Alarm vibrating sensor for a side."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:alarm"

    def __init__(self, coordinator, entry, side, device_info) -> None:
        super().__init__(coordinator)
        self._side = side
        self._attr_unique_id = f"{entry.entry_id}_{side}_alarm_vibrating"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Alarm Vibrating"

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.side_status(self._side).get(
            "isAlarmVibrating", False
        )


class FreeSleepSideOnSensor(
    CoordinatorEntity[FreeSleepCoordinator], BinarySensorEntity
):
    """Binary sensor showing if a side is actively running."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:power"

    def __init__(self, coordinator, entry, side, device_info) -> None:
        super().__init__(coordinator)
        self._side = side
        self._attr_unique_id = f"{entry.entry_id}_{side}_is_on"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Running"

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.side_status(self._side).get("isOn", False)


class FreeSleepPrimingSensor(
    CoordinatorEntity[FreeSleepCoordinator], BinarySensorEntity
):
    """Pod priming status sensor."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:water-pump"

    def __init__(self, coordinator, entry, device_info) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_is_priming"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Priming"

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.is_priming


class FreeSleepServerHealthSensor(
    CoordinatorEntity[FreeSleepCoordinator], BinarySensorEntity
):
    """Server health diagnostic sensor."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:server"

    def __init__(self, coordinator, entry, device_info) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_server_health"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Server Health Problem"

    @property
    def is_on(self) -> bool:
        """Return True if there is a server health problem."""
        return not self.coordinator.data.is_server_healthy()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return server status details."""
        attrs: dict[str, Any] = {}
        critical = ["franken", "database", "biometricsStream"]
        for svc in critical:
            status = self.coordinator.data.server_service_status(svc)
            attrs[f"{svc}_status"] = status.get("status", "unknown")
            if msg := status.get("message"):
                attrs[f"{svc}_message"] = msg
        return attrs
