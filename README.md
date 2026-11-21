# Hunter NODE-BT for Home Assistant

Control a **Hunter NODE-BT** battery irrigation controller from Home Assistant over Bluetooth. No cloud, no Hunter account, and no extra hub beyond the Bluetooth you already use with Home Assistant.

[![hacs][hacs-badge]][hacs]
<a href="https://www.buymeacoffee.com/deekay2153"><img src="https://img.shields.io/badge/Buy%20me%20a%20coffee-ffdd00?logo=buymeacoffee&logoColor=000" alt="Buy me a coffee"></a>

> Not affiliated with or endorsed by Hunter Industries. "Hunter" and "NODE-BT" are their trademarks. Use at your own risk.

## What you get

For each Node:

| Entity | What it does |
|---|---|
| `switch` Zone *N* | On = water that zone for its run time. Off = stop watering (see [Stopping](#stopping)). |
| `number` Zone *N* run time | Minutes the switch waters for (1–60, default 10). Stored in Home Assistant and kept across restarts. |
| `sensor` Zone *N* time remaining | Seconds left in the current run. |
| `sensor` Status | What the controller is doing: idle, manual zone run, program A/B/C running, rain off, rain delay, and so on. |
| `sensor` Battery | Battery % (diagnostic). Attribute `battery_changed` = the date the app recorded a battery change. |
| `sensor` Next run | When the Node's own program starts next. Attribute `programs` lists the programs it has set, e.g. `A "Summer": every day at 06:30, 17:30, zone 1 15 min`. |

The run time is sent to the Node with the start command, so the **Node turns the water off by itself** when the time is up, even if Home Assistant or Bluetooth drops out mid-run.

## Requirements

- Home Assistant 2024.12 or newer with the **Bluetooth** integration working, through either:
  - a Bluetooth adapter on the Home Assistant machine, or
  - an **ESPHome Bluetooth proxy** (recommended; place it near the Node).
- The proxy or adapter must make *active connections*. For ESPHome that's `bluetooth_proxy: active: true`.
- Reasonable signal. Connections work down to about -85 dBm; weaker than about -90 dBm usually fails. Nodes inside valve boxes with metal or concrete lids lose a lot of signal.

## Install

**HACS (recommended)**
1. HACS → three-dot menu → *Custom repositories* → add `https://github.com/deekay2153/hunter-node-bt`, type *Integration*.
2. Install **Hunter NODE-BT**, then restart Home Assistant.

**Manual:** copy `custom_components/hunter_node` into your `config/custom_components/` folder and restart.

## Set up

*Settings → Devices & services → Add integration → Hunter NODE-BT.*

| Field | What to enter |
|---|---|
| Node | Pick it from the list (it shows the name you gave it in the Hunter app). If it isn't listed, type its Bluetooth address. |
| Name | What to call it in Home Assistant, e.g. *Front garden*. |
| PIN | `0` unless you set a passcode in the Hunter app. |
| Zones | Tick the zones (stations) wired on this Node: 1 on a single-station Node, up to 4 on bigger models. |

You can change the PIN or zones later with **Configure** on the integration.

**Close the Hunter app first.** A Node takes one Bluetooth connection at a time. While the phone app is connected, Home Assistant can't reach it, and the other way round.

## How it talks to the Node

Every action is one short session: connect, log in with the PIN, send the command, read the state, disconnect. That takes about 5–10 seconds depending on signal. The Node runs on batteries, so connections are kept rare:

- **Idle:** one check every **30 minutes** (state, battery and programs together).
- **While watering:** a check every **30 seconds**, so the countdown and the stop show up quickly.

A run started by the Node's own program or the Hunter app is picked up at the next idle check, so it can show up to 30 minutes late. Runs started from Home Assistant show at once.

An unreachable Node shows its entities as *unavailable* until the next successful check. A single missed check is normal at the edge of Bluetooth range.

## Stopping

The Node has one stop command: **stop all**. Turning off any zone switch stops every zone on that Node. That makes no difference on a single-zone Node.

## Example: water at 6:30 unless it rained

```yaml
automation:
  - alias: Garden morning water
    triggers:
      - trigger: time
        at: "06:30:00"
    conditions:
      - condition: numeric_state
        entity_id: sensor.rain_today   # any rain sensor you have
        below: 2
    actions:
      - action: number.set_value
        target:
          entity_id: number.front_garden_zone_1_run_time
        data:
          value: 15
      - action: switch.turn_on
        target:
          entity_id: switch.front_garden_zone_1
```

If Home Assistant owns your schedule, set the Node's own programs to 0 minutes in the Hunter app so it doesn't water twice.

## Safety

The integration can only send this short list of commands. Anything else is refused in code before it reaches Bluetooth:

- read the controller's state and settings,
- start one zone for at most 60 minutes,
- stop all.

It **never** sends firmware, bootloader or over-the-air updates, a factory reset, or changes to the Node's programs, clock or PIN.

## Tested on

- Single-station NODE-BT units, PIN 0, through ESPHome Bluetooth proxies.

**Not yet tested:** 2- and 4-station Nodes, and Nodes with a passcode set. They follow the same protocol and should work. If you have one, please open an issue saying whether it worked.

## Troubleshooting

| You see | Try |
|---|---|
| Node missing from the list | Make sure the Hunter app is closed, check the proxy sees it (*Settings → Bluetooth → Advertisement monitor*), or type the address. |
| "not in range of a Bluetooth proxy" | Move a proxy closer. The Node must be reachable with an active connection, not just heard. |
| "PIN login rejected" | Wrong PIN. Change it with **Configure**. |
| Entities often unavailable | Weak signal. Check the RSSI in the advertisement monitor and aim for better than -85 dBm. |

For details, add this to `configuration.yaml`:
```yaml
logger:
  logs:
    custom_components.hunter_node: debug
```

## A dashboard for it

[Arcane Irrigation Card](https://github.com/deekay2153/arcane-irrigation-card) draws your yards with a living sky and sprinklers that spray while a zone runs. It works with this integration's entities as they are. For a Node named *Front garden*:

```yaml
type: custom:arcane-irrigation-card
zones:
  - entity: switch.front_garden_zone_1
    name: Front garden
    scene: front_garden
    remaining: sensor.front_garden_zone_1_time_remaining
    battery: sensor.front_garden_battery
    status: sensor.front_garden_status
```

## Protocol

See [PROTOCOL.md](PROTOCOL.md) for how the Node talks over Bluetooth.

## Support

If this saves you a trip to the valve box, you can [buy me a coffee](https://www.buymeacoffee.com/deekay2153). ☕

[hacs]: https://hacs.xyz
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
