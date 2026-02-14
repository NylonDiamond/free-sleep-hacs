"""DataUpdateCoordinator for Free Sleep."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

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
        server_status: dict[str, Any],
    ) -> None:
        """Initialize."""
        self.device_status = device_status
        self.settings = settings
        self.presence = presence
        self.schedules = schedules
        self.services = services
        self.vitals_summary = vitals_summary
        self.last_sleep = last_sleep
        self.server_status = server_status

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
        """Return the day-of-week key for the *next* alarm.

        Uses noon-crossover logic matching the web app: if the current
        time is noon or later the target day is tomorrow, otherwise today.
        """
        now = dt_util.now()
        if now.hour >= 12:
            target = now + timedelta(days=1)
        else:
            target = now
        return DAYS_OF_WEEK[target.weekday()]

    def today_alarm(self, side: str) -> dict[str, Any]:
        """Get the next alarm config for a side (noon-crossover)."""
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

    # ── Schedule override helpers ────────────────────────────────────

    def alarm_override(self, side: str) -> dict[str, Any]:
        """Get the alarm schedule override for a side."""
        return (
            self.side_settings(side)
            .get("scheduleOverrides", {})
            .get("alarm", {})
        )

    def is_alarm_disabled_tonight(self, side: str) -> bool:
        """Return True if the alarm is temporarily disabled for tonight.

        The override is active only when ``disabled`` is True **and**
        ``expiresAt`` is still in the future.
        """
        override = self.alarm_override(side)
        if not override.get("disabled", False):
            return False
        expires_at = override.get("expiresAt", "")
        if not expires_at:
            return False
        try:
            expires = dt_util.parse_datetime(expires_at)
            if expires is None:
                return False
            return expires > dt_util.now()
        except (ValueError, TypeError):
            return False

    def tonight_alarm(self, side: str) -> dict[str, Any]:
        """Get the alarm config for 'tonight' (alias for today_alarm)."""
        return self.today_alarm(side)

    # ── Tap gesture helpers ──────────────────────────────────────────

    def tap_config(self, side: str, gesture: str) -> dict[str, Any]:
        """Return tap config for a gesture on a side."""
        return self.side_settings(side).get("taps", {}).get(gesture, {})

    # ── Device status extras ─────────────────────────────────────────

    def seconds_remaining(self, side: str) -> int:
        """Return seconds until side auto-shuts off (0 if off)."""
        return self.side_status(side).get("secondsRemaining", 0)

    def gain(self, side: str) -> int:
        """Return heating/cooling gain (power multiplier) for a side."""
        key = f"gain{side.title()}"
        return self.device_status.get("settings", {}).get(key, 100)

    # ── Reboot daily ─────────────────────────────────────────────────

    @property
    def reboot_daily_enabled(self) -> bool:
        """Return True if daily reboot is enabled."""
        return self.settings.get("rebootDaily", False)

    # ── Next alarm timestamp ─────────────────────────────────────────

    def next_alarm_datetime(self, side: str) -> dt_util.dt.datetime | None:
        """Return the next alarm as a datetime object, or None if disabled."""
        alarm = self.today_alarm(side)
        if not alarm.get("enabled", False):
            return None
        if self.is_alarm_disabled_tonight(side):
            return None
        time_str = alarm.get("time", "")
        if not time_str:
            return None
        try:
            parts = time_str.split(":")
            hour, minute = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            return None
        now = dt_util.now()
        if now.hour >= 12:
            target_date = (now + timedelta(days=1)).date()
        else:
            target_date = now.date()
        tz = dt_util.get_default_time_zone()
        return dt_util.dt.datetime(
            target_date.year, target_date.month, target_date.day,
            hour, minute, 0, tzinfo=tz,
        )

    # ── Temperature schedule override ────────────────────────────────

    def temp_schedule_override(self, side: str) -> dict[str, Any]:
        """Get the temperature schedule override for a side."""
        return (
            self.side_settings(side)
            .get("scheduleOverrides", {})
            .get("temperatureSchedules", {})
        )

    def is_temp_schedule_disabled_tonight(self, side: str) -> bool:
        """Return True if temp schedules are temporarily disabled for tonight."""
        override = self.temp_schedule_override(side)
        if not override.get("disabled", False):
            return False
        expires_at = override.get("expiresAt", "")
        if not expires_at:
            return False
        try:
            expires = dt_util.parse_datetime(expires_at)
            if expires is None:
                return False
            return expires > dt_util.now()
        except (ValueError, TypeError):
            return False

    # ── Server status helpers ────────────────────────────────────────

    def server_service_status(self, service_name: str) -> dict[str, Any]:
        """Get status dict for a specific server service."""
        return self.server_status.get(service_name, {})

    def is_server_healthy(self) -> bool:
        """Return True if all critical services are healthy."""
        critical = ["franken", "database", "biometricsStream"]
        for svc in critical:
            status = self.server_service_status(svc).get("status", "unknown")
            if status in ("failed", "not_started"):
                return False
        return True


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
            device_status, settings, presence, schedules, services, server_status = (
                await asyncio.gather(
                    self.api.get_device_status(),
                    self.api.get_settings(),
                    self.api.get_presence(),
                    self.api.get_schedules(),
                    self.api.get_services(),
                    self.api.get_server_status(),
                )
            )

            # Vitals & sleep (heavier queries, may 404 if biometrics off)
            now = dt_util.now()
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
                server_status=server_status,
            )
        except FreeSleepApiError as err:
            raise UpdateFailed(f"Error communicating with Free Sleep: {err}") from err
