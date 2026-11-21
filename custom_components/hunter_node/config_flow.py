from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import CONF_PIN, CONF_STATION, CONF_STATIONS, DOMAIN, STATION_CHOICES

NUS_SERVICE = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
ZONES = {n: f"Zone {n}" for n in STATION_CHOICES}
PIN_FIELD = vol.All(vol.Coerce(int), vol.Range(0, 65535))


def _zones(value) -> list[int]:
    return sorted({int(z) for z in value})


def _current_zones(data) -> list[int]:
    if CONF_STATIONS in data:
        return list(data[CONF_STATIONS])
    return [data.get(CONF_STATION, 1)]


class HunterNodeConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return HunterNodeOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            address = user_input[CONF_ADDRESS].upper()
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            if not user_input[CONF_STATIONS]:
                errors[CONF_STATIONS] = "no_zones"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={
                        CONF_ADDRESS: address,
                        CONF_NAME: user_input[CONF_NAME],
                        CONF_PIN: user_input[CONF_PIN],
                        CONF_STATIONS: _zones(user_input[CONF_STATIONS]),
                    },
                )

        seen = {
            info.address: f"{info.name} ({info.address}, {info.rssi} dBm)"
            for info in bluetooth.async_discovered_service_info(self.hass, connectable=True)
            if NUS_SERVICE in info.service_uuids and info.address not in self._async_current_ids()
        }
        address_field = vol.In(seen) if seen else str
        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): address_field,
                    vol.Required(CONF_NAME): str,
                    vol.Required(CONF_PIN, default=0): PIN_FIELD,
                    vol.Required(CONF_STATIONS, default=[1]): cv.multi_select(ZONES),
                }
            ),
        )


class HunterNodeOptionsFlow(OptionsFlow):
    """Change the PIN or which zones get entities, without removing the Node."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self.config_entry
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input[CONF_STATIONS]:
                errors[CONF_STATIONS] = "no_zones"
            else:
                data = {k: v for k, v in entry.data.items() if k != CONF_STATION}
                data[CONF_PIN] = user_input[CONF_PIN]
                data[CONF_STATIONS] = _zones(user_input[CONF_STATIONS])
                self.hass.config_entries.async_update_entry(entry, data=data)
                self.hass.config_entries.async_schedule_reload(entry.entry_id)
                return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PIN, default=entry.data.get(CONF_PIN, 0)): PIN_FIELD,
                    vol.Required(CONF_STATIONS, default=_current_zones(entry.data)): cv.multi_select(ZONES),
                }
            ),
        )
