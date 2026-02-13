"""Climate platform for Free Sleep."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MAX_TEMP_F, MIN_TEMP_F
from .coordinator import FreeSleepCoordinator, FreeSleepData

_LOGGER = logging.getLogger(__name__)

SIDES = ["left", "right"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Free Sleep climate entities."""
    coordinator: FreeSleepCoordinator = entry.runtime_data
    entities = [FreeSleepClimate(coordinator, entry, side) for side in SIDES]
    async_add_entities(entities)


class FreeSleepClimate(CoordinatorEntity[FreeSleepCoordinator], ClimateEntity):
    """Climate entity for one side of an Eight Sleep pod."""

    _attr_has_entity_name = True
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.HEAT_COOL, HVACMode.OFF]
    _attr_min_temp = MIN_TEMP_F
    _attr_max_temp = MAX_TEMP_F
    _attr_target_temperature_step = 1

    def __init__(
        self,
        coordinator: FreeSleepCoordinator,
        entry: ConfigEntry,
        side: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._side = side
        self._attr_unique_id = f"{entry.entry_id}_{side}_climate"
        self._attr_device_info = _device_info(coordinator, entry, side)

    @property
    def name(self) -> str:
        """Return entity name."""
        return "Temperature"

    @property
    def _side_status(self) -> dict[str, Any]:
        return self.coordinator.data.side_status(self._side)

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._side_status.get("currentTemperatureF")

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        return self._side_status.get("targetTemperatureF")

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        if self._side_status.get("isOn", False):
            return HVACMode.HEAT_COOL
        return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current HVAC action."""
        if not self._side_status.get("isOn", False):
            return HVACAction.OFF
        current = self._side_status.get("currentTemperatureF", 0)
        target = self._side_status.get("targetTemperatureF", 0)
        if current < target:
            return HVACAction.HEATING
        if current > target:
            return HVACAction.COOLING
        return HVACAction.IDLE

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.api.set_side_on(self._side, False)
        else:
            await self.coordinator.api.set_side_on(self._side, True)
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temp = kwargs.get("temperature")
        if temp is None:
            return
        await self.coordinator.api.set_side_temperature(self._side, int(temp))
        await self.coordinator.async_request_refresh()


def _device_info(
    coordinator: FreeSleepCoordinator,
    entry: ConfigEntry,
    side: str,
) -> dict[str, Any]:
    """Return device info for a side."""
    from homeassistant.helpers.device_registry import DeviceInfo

    data = coordinator.data
    side_name = data.side_name(side)
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{side}")},
        name=f"Eight Sleep - {side_name}",
        manufacturer="Eight Sleep",
        model=data.cover_version,
        sw_version=data.free_sleep_version,
        via_device=(DOMAIN, entry.entry_id),
    )
