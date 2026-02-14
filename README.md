# Free Sleep

Home Assistant integration for the [Eight Sleep Pod](https://www.eightsleep.com/) running the [free-sleep](https://github.com/throwaway31265/free-sleep) open-source firmware. Control your mattress temperature, alarms, and more -- entirely local, no cloud subscription required.

## Prerequisites

Your Eight Sleep Pod must already be running the **free-sleep** server. See the [free-sleep setup guide](https://github.com/throwaway31265/free-sleep) for instructions. The pod must be reachable on your local network.

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots in the top right corner and select **Custom repositories**
3. Add this repository URL and select **Integration** as the category
4. Click **Add**, then find **Free Sleep** in the HACS integration list
5. Click **Download**
6. Restart Home Assistant

### Manual

1. Copy the `custom_components/free_sleep` directory into your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings > Devices & Services > Add Integration**
2. Search for **Free Sleep**
3. Enter the IP address of your Eight Sleep Pod (port defaults to `3000`)

The integration will auto-detect your pod and create devices for the pod itself and each side (left/right).

## Entities

The integration creates **55 entities** across the pod and both bed sides.

### Climate

| Entity | Scope | Description |
|---|---|---|
| Temperature | Per side | Set target temperature (55-110 F), turn heating/cooling on/off. Shows current temperature and whether the side is actively heating, cooling, or idle. |

### Sensors

| Entity | Scope | Description |
|---|---|---|
| Water Level | Pod | `OK` or `Low` |
| WiFi Strength | Pod | Signal strength (%) |
| Cover Version | Pod | Mattress cover hardware version |
| Hub Version | Pod | Hub hardware version |
| Free Sleep Version | Pod | Server software version and branch |
| Current Temperature | Per side | Current mattress surface temperature |
| Avg Heart Rate | Per side | Average heart rate (last 12h) |
| Min Heart Rate | Per side | Minimum heart rate (last 12h) |
| Max Heart Rate | Per side | Maximum heart rate (last 12h) |
| Avg HRV | Per side | Average heart rate variability (last 12h) |
| Avg Breathing Rate | Per side | Average breathing rate (last 12h) |
| Last Sleep Duration | Per side | Duration of last sleep session (hours) |
| Times Exited Bed | Per side | Times the user left bed during last sleep |

### Binary Sensors

| Entity | Scope | Description |
|---|---|---|
| Priming | Pod | Whether the pod is currently priming its water system |
| Bed Presence | Per side | Whether someone is currently in bed |
| Alarm Vibrating | Per side | Whether the alarm vibration is active |
| Running | Per side | Whether heating/cooling is running |

### Switches

| Entity | Scope | Description |
|---|---|---|
| Prime Pod Daily | Pod | Toggle automatic daily water priming |
| Biometrics | Pod | Toggle biometric data collection (heart rate, HRV, etc.) |
| Away Mode | Per side | Toggle away mode (prevents heating/cooling) |
| Alarm Enabled | Per side | Toggle today's alarm |

### Numbers

| Entity | Scope | Range | Description |
|---|---|---|---|
| LED Brightness | Pod | 0-100 | Pod LED brightness |
| Alarm Vibration Intensity | Per side | 1-100 | Alarm vibration strength |
| Alarm Temperature | Per side | 55-110 F | Thermal alarm target temperature |
| Alarm Duration | Per side | 0-180 min | Alarm vibration duration |

### Selects

| Entity | Scope | Options | Description |
|---|---|---|---|
| Double Tap Action | Per side | Decrease Temp, Increase Temp, Dismiss Alarm, Snooze Alarm | Action on double tap |
| Triple Tap Action | Per side | Same as above | Action on triple tap |
| Quad Tap Action | Per side | Same as above | Action on quad tap |
| Alarm Vibration Pattern | Per side | `double`, `rise` | Vibration pattern for alarms |

### Time

| Entity | Scope | Description |
|---|---|---|
| Prime Pod Daily Time | Pod | Time of day for automatic priming |
| Alarm Time | Per side | Today's alarm time |

### Buttons

| Entity | Scope | Description |
|---|---|---|
| Prime Pod | Pod | Start water priming immediately |
| Reboot | Pod | Reboot the pod |
| Update Free Sleep | Pod | Trigger a free-sleep software update |

## Notes

- **Fully local** -- communicates directly with the pod over your local network. No cloud, no Eight Sleep account needed.
- **Polling interval** -- the integration polls the pod every 30 seconds.
- **Alarms operate on "today"** -- alarm entities (time, enabled, vibration settings) read and write the schedule for the current day of the week.
- **Vitals may be unavailable** -- heart rate, HRV, and breathing sensors return unavailable if biometrics is disabled or no sleep was recorded in the last 12 hours.
- **No authentication** -- the free-sleep API has no auth. Ensure your pod is on a trusted network.
