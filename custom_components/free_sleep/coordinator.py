"""DataUpdateCoordinator for Free Sleep."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FreeSleepApi, FreeSleepApiError
from .const import DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)

DAYS_OF_WEEK = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

SIDES = ["left", "right"]


class FreeSleepData:
    """Container for all Free Sleep data."""

    def __init__(
        self,
        device_status: dict[str, Any],
        settings: dict[str, Any],
        presence: dict[str, Any],
        schedules: dict[str, Any],
        services: dict[str, Any],
        vitals_summary: dict[str, dict[str, Any]],
        last_sleep: dict[str, dict[str, Any] | None],
    ) -> None:
        """Initialize."""
        self.device_status = device_status
        self.settings = settings
        self.presence = presence
        self.schedules = schedules
        self.services = services
        self.vitals_summary = vitals_summary
        self.last_sleep = last_sleep

    # ── Device status helpers ────────────────────────────────────────

    def side_status(self, side: str) -> dict[str, Any]:
        """Get status for a side (left/right)."""
        return self.device_status.get(side, {})

    @property
    def is_priming(self) -> bool:
        """Return True if the pod is priming."""
        return self.device_status.get("isPriming", False)

    @property
    def water_level(self) -> str:
        """Return water level status string."""
        return self.device_status.get("waterLevel", "unknown")

    @property
    def wifi_strength(self) -> int:
        """Return WiFi signal strength."""
        return self.device_status.get("wifiStrength", 0)

    @property
    def led_brightness(self) -> int:
        """Return LED brightness."""
        return self.device_status.get("settings", {}).get("ledBrightness", 0)

    @property
    def cover_version(self) -> str:
        """Return cover version."""
        return self.device_status.get("coverVersion", "Unknown")

    @property
    def hub_version(self) -> str:
        """Return hub version."""
        return self.device_status.get("hubVersion", "Unknown")

    @property
    def free_sleep_version(self) -> str:
        """Return free-sleep server version."""
        fs = self.device_status.get("freeSleep", {})
        return fs.get("version", "Unknown")

    @property
    def free_sleep_branch(self) -> str:
        """Return free-sleep branch."""
        fs = self.device_status.get("freeSleep", {})
        return fs.get("branch", "Unknown")

    # ── Settings helpers ─────────────────────────────────────────────

    def side_settings(self, side: str) -> dict[str, Any]:
        """Get settings for a side."""
        return self.settings.get(side, {})

    def side_name(self, side: str) -> str:
        """Get the user-configured name for a side."""
        return self.side_settings(side).get("name", side.title())

    def away_mode(self, side: str) -> bool:
        """Return True if away mode is on for a side."""
        return self.side_settings(side).get("awayMode", False)

    @property
    def prime_daily_enabled(self) -> bool:
        """Return True if daily priming is enabled."""
        return self.settings.get("primePodDaily", {}).get("enabled", False)

    @property
    def prime_daily_time(self) -> str:
        """Return the daily prime time as HH:MM."""
        return self.settings.get("primePodDaily", {}).get("time", "14:00")

    # ── Presence helpers ─────────────────────────────────────────────

    def is_present(self, side: str) -> bool:
        """Return True if presence detected on a side."""
        return self.presence.get(side, {}).get("present", False)

    # ── Schedule helpers ─────────────────────────────────────────────

    @staticmethod
    def _today_key() -> str:
        """Return today's day-of-week key matching the schedule schema."""
        return DAYS_OF_WEEK[datetime.now().weekday()]

    def today_alarm(self, side: str) -> dict[str, Any]:
        """Get today's alarm config for a side."""
        day = self._today_key()
        return (
            self.schedules.get(side, {}).get(day, {}).get("alarm", {})
        )

    # ── Services helpers ─────────────────────────────────────────────

    @property
    def biometrics_enabled(self) -> bool:
        """Return True if biometrics is enabled."""
        return self.services.get("biometrics", {}).get("enabled", False)

    # ── Vitals helpers ───────────────────────────────────────────────

    def side_vitals_summary(self, side: str) -> dict[str, Any]:
        """Return vitals summary for a side (last night)."""
        return self.vitals_summary.get(side, {})

    # ── Sleep helpers ────────────────────────────────────────────────

    def side_last_sleep(self, side: str) -> dict[str, Any] | None:
        """Return the last sleep record for a side."""
        return self.last_sleep.get(side)

    # ── Tap gesture helpers ──────────────────────────────────────────

    def tap_config(self, side: str, gesture: str) -> dict[str, Any]:
        """Return tap config for a gesture on a side."""
        return self.side_settings(side).get("taps", {}).get(gesture, {})


class FreeSleepCoordinator(DataUpdateCoordinator[FreeSleepData]):
    """Coordinator to manage fetching Free Sleep data."""

    def __init__(self, hass: HomeAssistant, api: FreeSleepApi) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.api = api

    async def _async_update_data(self) -> FreeSleepData:
        """Fetch data from the Free Sleep API."""
        try:
            import asyncio

            # Core data (fast endpoints)
            device_status, settings, presence, schedules, services = (
                await asyncio.gather(
                    self.api.get_device_status(),
                    self.api.get_settings(),
                    self.api.get_presence(),
                    self.api.get_schedules(),
                    self.api.get_services(),
                )
            )

            # Vitals & sleep (heavier queries, may 404 if biometrics off)
            now = datetime.now()
            # Look back 12 hours for "last night"
            start = (now - timedelta(hours=12)).isoformat()
            end = now.isoformat()

            vitals_summary: dict[str, dict[str, Any]] = {}
            last_sleep: dict[str, dict[str, Any] | None] = {}

            for side in SIDES:
                try:
                    vitals_summary[side] = await self.api.get_vitals_summary(
                        side, start, end
                    )
                except Exception:
                    vitals_summary[side] = {}

                try:
                    records = await self.api.get_sleep_records(side, start, end)
                    last_sleep[side] = records[-1] if records else None
                except Exception:
                    last_sleep[side] = None

            return FreeSleepData(
                device_status=device_status,
                settings=settings,
                presence=presence,
                schedules=schedules,
                services=services,
                vitals_summary=vitals_summary,
                last_sleep=last_sleep,
            )
        except FreeSleepApiError as err:
            raise UpdateFailed(f"Error communicating with Free Sleep: {err}") from err
