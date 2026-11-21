from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import HunterEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    c = entry.runtime_data
    async_add_entities([HunterZoneSwitch(c, "zone", n) for n in c.stations])


class HunterZoneSwitch(HunterEntity, SwitchEntity):
    """On = run this zone for its run-time setting. Off = Stop all (the Node has no single-zone stop)."""

    _attr_icon = "mdi:sprinkler-variant"

    @property
    def is_on(self) -> bool:
        return self.coordinator.is_running(self.station)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_start(self.station)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_stop()
