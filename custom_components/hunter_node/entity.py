from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HunterCoordinator


class HunterEntity(CoordinatorEntity[HunterCoordinator]):
    """Node-wide entities pass station=None; zone entities pass their zone number."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: HunterCoordinator, key: str, station: int | None = None) -> None:
        super().__init__(coordinator)
        address = coordinator.node.address
        self.station = station
        # Zone 1 keeps the plain key so entities from single-zone setups keep their unique ids.
        suffix = "" if station in (None, 1) else f"_{station}"
        self._attr_unique_id = f"{address}_{key}{suffix}"
        self._attr_translation_key = key
        if station is not None:
            self._attr_translation_placeholders = {"station": str(station)}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, address)},
            connections={(CONNECTION_BLUETOOTH, address)},
            name=coordinator.node.name,
            manufacturer="Hunter Industries",
            model="NODE-BT",
        )
