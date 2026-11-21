"""Hunter NODE-BT battery irrigation controller over Home Assistant Bluetooth (local adapter or ESPHome proxy)."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_PIN
from .coordinator import HunterCoordinator
from .protocol import HunterNode

PLATFORMS = [Platform.SWITCH, Platform.NUMBER, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    node = HunterNode(hass, entry.data[CONF_ADDRESS], entry.data[CONF_NAME], entry.data.get(CONF_PIN, 0))
    coordinator = HunterCoordinator(hass, entry, node)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
