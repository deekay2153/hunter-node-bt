from __future__ import annotations

from homeassistant.components.number import NumberMode, RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEFAULT_RUN_MINUTES
from .entity import HunterEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    c = entry.runtime_data
    async_add_entities([HunterRunTime(c, "run_time", n) for n in c.stations])


class HunterRunTime(HunterEntity, RestoreNumber):
    """How long the zone switch waters for. Kept in HA, not on the Node."""

    _attr_native_min_value = 1
    _attr_native_max_value = 60
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:timer-outline"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last and last.native_value is not None:
            self.coordinator.run_minutes[self.station] = int(last.native_value)
        else:
            self.coordinator.run_minutes[self.station] = DEFAULT_RUN_MINUTES

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> float:
        return self.coordinator.run_minutes[self.station]

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.run_minutes[self.station] = int(value)
        self.async_write_ha_state()
