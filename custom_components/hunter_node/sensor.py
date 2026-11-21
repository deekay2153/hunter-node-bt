from __future__ import annotations

from datetime import datetime, timedelta, timezone

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import CONTROLLER_STATES
from .entity import HunterEntity

UNUSED = 65535


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    c = entry.runtime_data
    async_add_entities(
        [
            *(HunterRemaining(c, "time_remaining", n) for n in c.stations),
            HunterStatus(c, "status"),
            HunterBattery(c, "battery"),
            HunterNextRun(c, "next_run"),
        ]
    )


def _hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def describe_program(letter: str, prog: dict, stations: list[int]) -> str | None:
    """'A "Summer": every day at 06:30, 17:30, zone 1 15 min, zone 2 10 min', or None if it waters none of them."""
    starts = [s for s in prog.get("StartTimes", []) if s != UNUSED]
    runs = prog.get("RunTime", [])
    lengths = [(n, runs[n - 1]) for n in stations if len(runs) >= n and runs[n - 1]]
    if not starts or not lengths:
        return None
    stype, days = prog.get("ScheduleType"), prog.get("ScheduleDays")
    if stype == 0 and days == 127:
        when = "every day"
    elif stype == 1:
        when = f"every {prog.get('IntervalDayCount')} days"
    else:
        when = f"schedule type {stype}, days {days}"
    zones = ", ".join(f"zone {n} {round(r / 60)} min" for n, r in lengths)
    return f'{letter} "{prog.get("Name", "")}": {when} at {", ".join(_hhmm(s) for s in starts)}, {zones}'


class HunterRemaining(HunterEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_suggested_display_precision = 0
    _attr_icon = "mdi:timer-sand"

    @property
    def native_value(self) -> int:
        st = self.coordinator.station_state(self.station) or {}
        return int(st.get("Remaining", 0)) if self.coordinator.is_running(self.station) else 0


class HunterStatus(HunterEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = CONTROLLER_STATES

    @property
    def native_value(self) -> str | None:
        cs = (self.coordinator.data or {}).get("ControllerState")
        if isinstance(cs, int) and 0 <= cs < len(CONTROLLER_STATES):
            return CONTROLLER_STATES[cs]
        return None

    @property
    def extra_state_attributes(self) -> dict:
        d = self.coordinator.data or {}
        return {
            "next_water_time": d.get("NextWaterTime"),
            "daily_run_time": d.get("DailyRunTime"),
            "click_sensor": d.get("ClickSensorState"),
        }


class HunterBattery(HunterEntity, SensorEntity):
    """Node battery %, read on idle polls (every 30 min)."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> int | None:
        return self.coordinator.settings.get("Sensor", {}).get("Battery")

    @property
    def extra_state_attributes(self) -> dict:
        changed = self.coordinator.settings.get("Controller", {}).get("BatteryChangeDate")
        # Node times are local wall-clock seconds stored as if UTC.
        date = datetime.fromtimestamp(changed, timezone.utc).date().isoformat() if changed else None
        return {"battery_changed": date}


class HunterNextRun(HunterEntity, SensorEntity):
    """Next programmed start, from the Node's NextWaterTime (minutes after local midnight)."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self) -> datetime | None:
        minutes = (self.coordinator.data or {}).get("NextWaterTime")
        if not isinstance(minutes, int) or not 0 <= minutes < 24 * 60:
            return None
        now = dt_util.now()
        start = dt_util.start_of_local_day(now) + timedelta(minutes=minutes)
        if start <= now:
            start += timedelta(days=1)
        return start

    @property
    def extra_state_attributes(self) -> dict:
        s = self.coordinator.settings
        progs = [
            d
            for letter in "ABC"
            if (d := describe_program(letter, s.get(f"Program_{letter}", {}), self.coordinator.stations))
        ]
        return {"programs": progs, "season_adjust": s.get("Controller", {}).get("SeasonAdjust")}
