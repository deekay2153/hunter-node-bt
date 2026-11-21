from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_STATION, CONF_STATIONS, DEFAULT_RUN_MINUTES, IDLE_INTERVAL, RUNNING_INTERVAL
from .protocol import READ_ALL, READ_STATE, STOP_ALL, HunterError, HunterNode, start_station

_LOGGER = logging.getLogger(__name__)


def station_running(station: dict | None) -> bool:
    """Same rule as the Hunter app: 3 watering, 4 soaking, 2 counts while time remains."""
    if not station:
        return False
    s, rem = station.get("State", 0), station.get("Remaining", 0)
    return s in (3, 4) or (s == 2 and rem > 0)


def configured_stations(data) -> list[int]:
    """Zones set up for this Node (older entries stored a single `station`)."""
    if CONF_STATIONS in data:
        return list(data[CONF_STATIONS])
    return [data.get(CONF_STATION, 1)]


class HunterCoordinator(DataUpdateCoordinator[dict]):
    """data = the Node's "State" section."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, node: HunterNode) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=node.name, update_interval=IDLE_INTERVAL)
        self.node = node
        self.stations = configured_stations(entry.data)
        self.run_minutes = {n: DEFAULT_RUN_MINUTES for n in self.stations}
        self.settings: dict = {}  # last {"Read":"All"} reply: Controller, Sensor, Program_A.., Station_N

    def station_state(self, station: int) -> dict | None:
        return (self.data or {}).get(f"Station_{station}")

    def is_running(self, station: int) -> bool:
        return station_running(self.station_state(station))

    @property
    def any_running(self) -> bool:
        return any(self.is_running(n) for n in self.stations)

    def _apply(self, state: dict) -> dict:
        running = any(station_running(state.get(f"Station_{n}")) for n in self.stations)
        self.update_interval = RUNNING_INTERVAL if running else IDLE_INTERVAL
        return state

    async def _async_update_data(self) -> dict:
        # Idle polls also fetch the full settings (battery, programs) in the same connection;
        # fast polls while watering only need the run state.
        cmds = [READ_STATE] if self.any_running else [READ_ALL, READ_STATE]
        try:
            replies = await self.node.session(cmds)
        except HunterError as err:
            raise UpdateFailed(str(err)) from err
        if len(replies) == 2:
            self.settings = replies[0]
        return self._apply(replies[-1]["State"])

    async def _command(self, cmd: dict) -> None:
        try:
            replies = await self.node.session([cmd, READ_STATE])
        except HunterError as err:
            raise HomeAssistantError(f"{self.node.name}: {err}") from err
        self.async_set_updated_data(self._apply(replies[-1]["State"]))

    async def async_start(self, station: int, minutes: int | None = None) -> None:
        seconds = int((minutes or self.run_minutes[station]) * 60)
        await self._command(start_station(station, seconds))

    async def async_stop(self) -> None:
        """The Node only has Stop all: stopping one zone stops every zone on this Node."""
        await self._command(STOP_ALL)
