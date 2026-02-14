"""API client for Free Sleep."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class FreeSleepApiError(Exception):
    """Exception for Free Sleep API errors."""


class FreeSleepConnectionError(FreeSleepApiError):
    """Exception for connection errors."""


class FreeSleepApi:
    """API client for the Free Sleep server running on an Eight Sleep pod."""

    def __init__(
        self,
        host: str,
        port: int,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the API client."""
        self._host = host
        self._port = port
        self._session = session
        self._base_url = f"http://{host}:{port}"

    @property
    def base_url(self) -> str:
        """Return the base URL."""
        return self._base_url

    async def _request(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | list[str] | None = None,
    ) -> Any:
        """Make a request to the Free Sleep API."""
        url = f"{self._base_url}{path}"
        try:
            async with self._session.request(
                method,
                url,
                json=json_data,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 204:
                    return None
                if resp.status >= 400:
                    text = await resp.text()
                    raise FreeSleepApiError(
                        f"API error {resp.status} for {method} {path}: {text}"
                    )
                return await resp.json()
        except aiohttp.ClientError as err:
            raise FreeSleepConnectionError(
                f"Connection error for {method} {path}: {err}"
            ) from err

    # ── Device Status ────────────────────────────────────────────────

    async def get_device_status(self) -> dict[str, Any]:
        """GET /api/deviceStatus - fetch current device state."""
        return await self._request("GET", "/api/deviceStatus")

    async def set_device_status(self, data: dict[str, Any]) -> None:
        """POST /api/deviceStatus - update device state (partial)."""
        await self._request("POST", "/api/deviceStatus", json_data=data)

    # ── Settings ─────────────────────────────────────────────────────

    async def get_settings(self) -> dict[str, Any]:
        """GET /api/settings - fetch settings."""
        return await self._request("GET", "/api/settings")

    async def set_settings(self, data: dict[str, Any]) -> dict[str, Any]:
        """POST /api/settings - update settings (partial merge)."""
        return await self._request("POST", "/api/settings", json_data=data)

    # ── Presence ─────────────────────────────────────────────────────

    async def get_presence(self) -> dict[str, Any]:
        """GET /api/metrics/presence - fetch bed presence."""
        return await self._request("GET", "/api/metrics/presence")

    # ── Jobs ─────────────────────────────────────────────────────────

    async def run_jobs(self, jobs: list[str]) -> None:
        """POST /api/jobs - trigger jobs (reboot, update, etc)."""
        await self._request("POST", "/api/jobs", json_data=jobs)

    # ── Convenience helpers ──────────────────────────────────────────

    async def set_side_on(self, side: str, on: bool) -> None:
        """Turn a side on or off."""
        await self.set_device_status({side: {"isOn": on}})

    async def set_side_temperature(self, side: str, temp_f: int) -> None:
        """Set target temperature for a side (Fahrenheit)."""
        await self.set_device_status({side: {"targetTemperatureF": temp_f}})

    async def set_led_brightness(self, brightness: int) -> None:
        """Set the LED brightness (0-100)."""
        await self.set_device_status({"settings": {"ledBrightness": brightness}})

    async def start_prime(self) -> None:
        """Start priming the pod."""
        await self.set_device_status({"isPriming": True})

    async def set_away_mode(self, side: str, enabled: bool) -> None:
        """Enable or disable away mode for a side."""
        await self.set_settings({side: {"awayMode": enabled}})

    async def set_prime_daily(self, enabled: bool) -> None:
        """Enable or disable daily priming."""
        await self.set_settings({"primePodDaily": {"enabled": enabled}})

    async def set_prime_daily_time(self, time_str: str) -> None:
        """Set daily prime time (HH:MM format)."""
        await self.set_settings({"primePodDaily": {"time": time_str}})

    async def reboot(self) -> None:
        """Reboot the pod."""
        await self.run_jobs(["reboot"])

    async def update(self) -> None:
        """Update the pod firmware."""
        await self.run_jobs(["update"])

    # ── Schedules ─────────────────────────────────────────────────────

    async def get_schedules(self) -> dict[str, Any]:
        """GET /api/schedules - fetch all schedules."""
        return await self._request("GET", "/api/schedules")

    async def set_schedules(self, data: dict[str, Any]) -> dict[str, Any]:
        """POST /api/schedules - update schedules (partial merge)."""
        return await self._request("POST", "/api/schedules", json_data=data)

    # ── Services ─────────────────────────────────────────────────────

    async def get_services(self) -> dict[str, Any]:
        """GET /api/services - fetch services config (biometrics, sentry)."""
        return await self._request("GET", "/api/services")

    async def set_services(self, data: dict[str, Any]) -> dict[str, Any]:
        """POST /api/services - update services config."""
        return await self._request("POST", "/api/services", json_data=data)

    # ── Vitals ───────────────────────────────────────────────────────

    async def get_vitals_summary(
        self, side: str, start_time: str, end_time: str
    ) -> dict[str, Any]:
        """GET /api/metrics/vitals/summary - aggregated vitals for a time range."""
        params = f"?side={side}&startTime={start_time}&endTime={end_time}"
        return await self._request("GET", f"/api/metrics/vitals/summary{params}")

    # ── Sleep ────────────────────────────────────────────────────────

    async def get_sleep_records(
        self, side: str, start_time: str, end_time: str
    ) -> list[dict[str, Any]]:
        """GET /api/metrics/sleep - sleep records for a time range."""
        params = f"?side={side}&startTime={start_time}&endTime={end_time}"
        return await self._request("GET", f"/api/metrics/sleep{params}")

    # ── Convenience helpers ──────────────────────────────────────────

    async def set_biometrics_enabled(self, enabled: bool) -> None:
        """Enable or disable biometrics."""
        await self.set_services({"biometrics": {"enabled": enabled}})

    async def set_alarm(
        self, side: str, day: str, alarm_data: dict[str, Any],
        current_alarm: dict[str, Any] | None = None,
    ) -> None:
        """Update alarm settings for a side and day.

        The server replaces the entire alarm object on POST, so we merge
        *alarm_data* into *current_alarm* to avoid wiping unrelated fields.
        """
        merged = dict(current_alarm or {})
        merged.update(alarm_data)
        await self.set_schedules({side: {day: {"alarm": merged}}})

    async def set_tap_config(
        self, side: str, gesture: str, config: dict[str, Any]
    ) -> None:
        """Update tap gesture config for a side."""
        await self.set_settings({side: {"taps": {gesture: config}}})

    async def test_connection(self) -> dict[str, Any]:
        """Test the connection by fetching device status."""
        return await self.get_device_status()

    # ── Server Status ────────────────────────────────────────────────

    async def get_server_status(self) -> dict[str, Any]:
        """GET /api/serverStatus - fetch health status of all services."""
        return await self._request("GET", "/api/serverStatus")

    # ── Alarm Trigger ────────────────────────────────────────────────

    async def trigger_alarm(
        self, side: str, vibration_intensity: int, vibration_pattern: str, duration: int
    ) -> None:
        """POST /api/alarm - trigger alarm vibration immediately."""
        await self._request(
            "POST",
            "/api/alarm",
            json_data={
                "side": side,
                "vibrationIntensity": vibration_intensity,
                "vibrationPattern": vibration_pattern,
                "duration": duration,
                "force": False,
            },
        )

    # ── Gain / Reboot Daily ───────────────────────────────────────────

    async def set_reboot_daily(self, enabled: bool) -> None:
        """Enable or disable daily reboot."""
        await self.set_settings({"rebootDaily": enabled})

    async def set_gain(self, side: str, gain: int) -> None:
        """Set heating/cooling gain (power multiplier) for a side.

        Gain is stored in device status settings, not main settings.
        """
        key = f"gain{side.title()}"
        await self.set_device_status({"settings": {key: gain}})
