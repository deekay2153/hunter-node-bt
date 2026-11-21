"""Hunter NODE-BT BLE protocol: PIN login + JSON over Nordic UART. See PROTOCOL.md in the repo.

Only the commands in validate() are ever sent. Firmware, bootloader, OTA and factory reset
are never used.
"""
from __future__ import annotations

import asyncio
import json
import logging

from bleak import BleakClient
from bleak_retry_connector import establish_connection

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

PIN_CHAR = "4c9dbe52-3566-4dfc-a299-4ea1353970e2"
MSG_RX = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
MSG_TX = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
CHUNK = 20
STEP_TIMEOUT = 15

READ_STATE = {"Read": "Section_State"}
READ_ALL = {"Read": "All"}
STOP_ALL = {"Manual": {"StopAll": True}}
ALLOWED_READS = {"All", "Section_State", "Section_Controller", "Section_Sensor", "LastRun"}


class HunterError(Exception):
    """Session failed."""


def start_station(station: int, seconds: int) -> dict:
    return {"Manual": {"StationNumber": station, "RunTime": seconds}}


def validate(cmd: dict) -> None:
    if set(cmd) == {"Read"} and cmd["Read"] in ALLOWED_READS:
        return
    if cmd == STOP_ALL:
        return
    if set(cmd) == {"Manual"} and isinstance(cmd["Manual"], dict):
        m = cmd["Manual"]
        if (
            set(m) == {"StationNumber", "RunTime"}
            and m["StationNumber"] in (1, 2, 3, 4)
            and isinstance(m["RunTime"], int)
            and 0 < m["RunTime"] <= 3600
        ):
            return
    raise HunterError(f"Command not allowed: {cmd}")


def _xor(b: bytes) -> bytes:
    return bytes((x ^ 0xAC) if x else 0 for x in b)


def _pin_packet(ptype: int, result: int = 0, rnd: int = 0, pin: int = 0) -> bytes:
    return bytes([ptype, result]) + rnd.to_bytes(2, "little") + pin.to_bytes(2, "little")


class HunterNode:
    """One connect-login-command-disconnect session at a time."""

    def __init__(self, hass: HomeAssistant, address: str, name: str, pin: int) -> None:
        self.hass = hass
        self.address = address
        self.name = name
        self.pin = pin
        self._lock = asyncio.Lock()

    async def session(self, commands: list[dict]) -> list[dict]:
        for c in commands:
            validate(c)
        async with self._lock:
            device = bluetooth.async_ble_device_from_address(self.hass, self.address, connectable=True)
            if device is None:
                raise HunterError(f"{self.name} ({self.address}) is not in range of a Bluetooth proxy")
            try:
                return await asyncio.wait_for(self._session(device, commands), 90)
            except HunterError:
                raise
            except Exception as err:  # noqa: BLE001 - bleak/proxy errors vary
                raise HunterError(f"{type(err).__name__}: {err}") from err

    async def _session(self, device, commands: list[dict]) -> list[dict]:
        pin_q: asyncio.Queue = asyncio.Queue()
        msg_q: asyncio.Queue = asyncio.Queue()
        client = await establish_connection(BleakClient, device, self.name, max_attempts=3)
        try:
            await client.start_notify(PIN_CHAR, lambda _c, d: pin_q.put_nowait(bytes(d)))
            await client.start_notify(MSG_TX, lambda _c, d: msg_q.put_nowait(bytes(d)))

            await client.write_gatt_char(PIN_CHAR, _xor(_pin_packet(1)), response=False)
            p = _xor(await asyncio.wait_for(pin_q.get(), STEP_TIMEOUT))
            if p[0] != 2 or p[1] != 0:
                raise HunterError(f"unexpected PIN challenge {p.hex(' ')}")
            rnd = int.from_bytes(p[2:4], "little")
            await client.write_gatt_char(PIN_CHAR, _xor(_pin_packet(3, 0, rnd, self.pin ^ rnd)), response=False)
            p = _xor(await asyncio.wait_for(pin_q.get(), STEP_TIMEOUT))
            if p[0] != 4 or p[1] != 0:
                raise HunterError("PIN login rejected (wrong PIN?)")

            replies = []
            for cmd in commands:
                text = json.dumps(cmd, separators=(",", ":"))
                data = text.encode()
                while not msg_q.empty():
                    msg_q.get_nowait()
                for i in range(0, len(data), CHUNK):
                    await client.write_gatt_char(MSG_RX, data[i : i + CHUNK], response=True)
                buf = b""
                while b"\x00" not in buf:
                    part = await asyncio.wait_for(msg_q.get(), STEP_TIMEOUT)
                    if buf and part.startswith(b"{"):
                        buf = b""
                    buf += part
                reply = buf.split(b"\x00", 1)[0].decode("utf-8", "replace")
                _LOGGER.debug("%s: %s -> %s", self.name, text, reply)
                try:
                    parsed = json.loads(reply)
                except ValueError as err:
                    raise HunterError(f"bad reply to {text}: {reply!r}") from err
                if "Status" in parsed and parsed["Status"] != 0:
                    raise HunterError(f"{text} failed with Status {parsed['Status']}")
                replies.append(parsed)
            return replies
        finally:
            await client.disconnect()
