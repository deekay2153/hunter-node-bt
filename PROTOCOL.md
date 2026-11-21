# Hunter NODE-BT Bluetooth protocol

Reverse-engineered from the official app, for interoperability. Only what this integration uses is described here.

## Services

| Service | Write | Notify / indicate | Use |
|---|---|---|---|
| `6e400001-b5a3-f393-e0a9-e50e24dcca9e` Nordic UART | `6e400002-…` | `6e400003-…` (indicate) | All commands, as JSON |
| `0ed3e3d3-8cd8-4f29-8fec-a7d3a2c5443e` PIN | `4c9dbe52-3566-4dfc-a299-4ea1353970e2` (write without response + notify) | same characteristic | PIN login |
| `0031f62c-…`, `3595f2c9-…`, `1d14d6ee-…` | | | Controller firmware, bootloader and Bluetooth OTA updates. **Never write to these.** |

## Session

1. Connect, then subscribe to notifications on the PIN characteristic and indications on `6e400003`.
2. Log in with the PIN (below). The official app tries `0` first, so a Node with no passcode accepts `0`.
3. Send commands one at a time, waiting for each reply.
4. Disconnect. The Node accepts only one connection at a time.

## PIN login

A packet is 6 bytes, little-endian: `type u8, result u8, random u16, pin u16`. In **both directions** every non-zero byte is XORed with `0xAC`; zero bytes stay zero. This is obfuscation, not encryption.

| Step | Direction | Plain packet |
|---|---|---|
| Login request | → | type `1`, everything else `0` |
| Challenge | ← | type `2`, result must be `0`, random = R |
| Challenge response | → | type `3`, result `0`, random R, pin = `PIN XOR R` |
| Result | ← | type `4`, result `0` = logged in, anything else = wrong PIN |

## Messages

- **Request:** compact JSON (no spaces), UTF-8, split into 20-byte chunks, each written to `6e400002`.
- **Reply:** UTF-8 on `6e400003`, possibly over several indications. A message starts with `{` and ends at the first `\0` byte.
- `{"Status":0}` = OK. Any other `Status` value is an error. Other replies are the section that was read.

| Purpose | Send | Reply |
|---|---|---|
| Start a zone | `{"Manual":{"StationNumber":1,"RunTime":600}}` (seconds) | `{"Status":0}` |
| Stop everything | `{"Manual":{"StopAll":true}}` | `{"Status":0}` |
| Read run state | `{"Read":"Section_State"}` | `{"State":{…}}` |
| Read everything | `{"Read":"All"}` | Controller, Sensor, Program_A/B/C, Station_N, State |

The app has more commands (program edits, clock, seasonal adjust, controller off, factory reset). This integration doesn't send any of them, and its code refuses to.

## State

`State` holds `ControllerState`, `ClickSensorState`, `SoilSensorPercentage`, `NextWaterTime` (minutes after local midnight), `DailyRunTime` and `Station_1`…`Station_4` = `{Number, State, Remaining}`.

`ControllerState`: 0 idle, 1 manual zone, 2 off, 3 days off, 4 rain off, 5 rain delay, 6 soil off, 7–9 program A/B/C running, 10 manual run all, 11–13 manual program A/B/C.

Station `State`: **3 = watering**, 4 = soaking (cycle-and-soak pause), 2 = counted as active while `Remaining > 0`. `Remaining` is seconds left.

In `{"Read":"All"}`, times such as `BatteryChangeDate` are local wall-clock seconds stored as if they were UTC. `Sensor.Battery` is the battery percentage. Each `Program_X` has `Name`, `StartTimes` (minutes after midnight, `65535` = unused), `RunTime` (seconds per station), `ScheduleType` and `ScheduleDays`.
