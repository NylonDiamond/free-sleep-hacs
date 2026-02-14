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

SIDES = ["left", "right"]


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

    entities: list[ButtonEntity] = [
        FreeSleepWebAppButton(coordinator, entry, pod_device),
        FreeSleepPrimeButton(coordinator, entry, pod_device),
        FreeSleepRebootButton(coordinator, entry, pod_device),
        FreeSleepUpdateButton(coordinator, entry, pod_device),
    ]

    for side in SIDES:
        side_device = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{side}")},
        )
        entities.append(FreeSleepTriggerAlarmButton(coordinator, entry, side, side_device))

    async_add_entities(entities)


class FreeSleepWebAppButton(
    CoordinatorEntity[FreeSleepCoordinator], ButtonEntity
):
    """Button to open the Free Sleep web app."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:web"
    _attr_entity_category = "diagnostic"

    def __init__(self, coordinator, entry, device_info) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_web_app"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Open Web App"

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the web app URL."""
        return {"url": self.coordinator.api.base_url}

    async def async_press(self) -> None:
        """Press the button - opens web app (handled by frontend)."""
        # The button press itself doesn't do anything server-side
        # The URL is exposed in extra_state_attributes for the frontend
        pass


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


class FreeSleepTriggerAlarmButton(
    CoordinatorEntity[FreeSleepCoordinator], ButtonEntity
):
    """Button to trigger alarm vibration immediately."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:alarm-bell"

    def __init__(self, coordinator, entry, side, device_info) -> None:
        super().__init__(coordinator)
        self._side = side
        self._attr_unique_id = f"{entry.entry_id}_{side}_trigger_alarm"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return "Trigger Alarm"

    async def async_press(self) -> None:
        """Press the button - trigger alarm using tonight's settings."""
        alarm = self.coordinator.data.tonight_alarm(self._side)
        intensity = alarm.get("vibrationIntensity", 100)
        pattern = alarm.get("vibrationPattern", "rise")
        duration = alarm.get("duration", 10)
        await self.coordinator.api.trigger_alarm(
            self._side, intensity, pattern, duration
        )
