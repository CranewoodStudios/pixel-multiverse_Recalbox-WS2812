# Architecture

This document is the primary technical reference for the host-side Recalbox LED
system.

The host side is deliberately small. Recalbox event scripts translate platform
events into daemon commands, and the daemon turns those commands into USB CDC
LED frames for a separate Picade Max controller firmware.

## Component Responsibilities

- Recalbox event scripts: lightweight shell hooks called by Recalbox or
  EmulationStation.
- `pmctl`: validates simple commands and writes JSON events to `/tmp/pm.fifo`.
- `/tmp/pm.fifo`: local command queue between scripts and the daemon.
- `pm_daemon.py`: loads JSON configuration, tracks idle animation state, renders
  LED frames, and writes them to the controller over USB CDC.
- `recalbox/config/systems.json`: system accents, menu defaults, game-start
  layouts, and ROM-specific layout overrides.
- `recalbox/config/buttons.json`: button LED count, coordinate mapping, and
  attract mode pattern program.
- Compatible Picade Max firmware: external project that receives USB CDC frames
  and drives WS2812 LEDs.

## Event Flow

```text
Recalbox Event Scripts
        |
        v
      pmctl
        |
        v
   /tmp/pm.fifo
        |
        v
   pm_daemon.py
        |
        | USB CDC
        v
External Picade Max Firmware
```

## Sequence

```text
Recalbox hook        pmctl              FIFO              daemon            firmware
     |                 |                 |                  |                  |
     | game-start      |                 |                  |                  |
     |---------------->|                 |                  |                  |
     |                 | JSON line       |                  |                  |
     |                 |---------------->|                  |                  |
     |                 |                 | poll/read        |                  |
     |                 |                 |----------------->|                  |
     |                 |                 |                  | render frames    |
     |                 |                 |                  |----------------->|
```

## Daemon Lifecycle

On startup the daemon:

1. Loads `systems.json`.
2. Loads `buttons.json`.
3. Creates `/tmp/pm.fifo` when needed.
4. Opens the FIFO and enters the polling loop.
5. Attempts to auto-detect and open a serial device, preferring
   `/dev/serial/by-id` entries whose names include Picade, Pimoroni, or Max.

The daemon remains running if no USB CDC serial device is available. It retries
serial discovery periodically while continuing to process FIFO commands. The
latest intended LED frame is retained and resent when USB reconnects.

The daemon handles `SIGINT` and `SIGTERM` by leaving the polling loop, sending
an all-off frame when possible, closing the serial port, and closing the FIFO
handles.

## Runtime State

The daemon keeps one authoritative current state. Commands received through the
FIFO request transitions into that state, and the state determines whether idle
output continues or a fixed frame should remain displayed.

Current states:

- `MENU`: menu idle breathing output, optionally using the current system
  accent.
- `GAME_RUNNING`: game-running idle breathing output using the current system
  accent when available.
- `ATTRACT`: attract idle output from `buttons.json` pattern configuration or
  the default attract mode.
- `SOLID`: persistent solid colour from `pmctl solid B G R BR`.
- `OFF`: persistent all-off output.
- `SHUTDOWN`: persistent all-off output after the shutdown animation.
- `REBOOT`: persistent all-off output after the reboot animation.

Current command transitions:

| Command | Entry behavior | Resulting state |
| --- | --- | --- |
| startup | load configuration and open FIFO | `MENU` |
| `menu` | menu pulse animation | `MENU` |
| `game-start` | game start layout or wipe animation | `GAME_RUNNING` |
| `game-end` | game end animation | `MENU` |
| `attract-on` | none | `ATTRACT` |
| `attract-off` | none | `MENU` |
| `solid` | send requested solid frame | `SOLID` |
| `off` | send all-off frame | `OFF` |
| `shutdown` | shutdown animation, then all-off | `SHUTDOWN` |
| `reboot` | reboot animation, then all-off | `REBOOT` |
| `settings-changed` / `controls-changed` | notification blink | previous state |
| `reload-config` | reload configuration | previous state |

Duplicate state requests are harmless. They do not create a second state object
or change the retained state identity, although existing command entry
animations may still run before the duplicate transition is detected.

Known future work, such as non-blocking animations, interruptible fades, and
live configuration reload validation, should be kept as separate functional
changes.

## Frame Output And Fading

The daemon generates logical LED frames as `(B, G, R, brightness)` tuples.
Brightness is applied by frame generation and configuration parsing before a
frame is packed for USB. The host does not apply a second global brightness
scale during transmission.

Frame output tracks the last generated frame. Persistent fixed states such as
`SOLID` and `OFF` can start an interruptible fade from that tracked frame to the
target frame. Fade updates are advanced from the main daemon loop using
monotonic time and return control immediately after at most one generated frame.

## Deployment Architecture

The repository keeps source files under `recalbox/`. The deployed Recalbox
runtime is flattened under:

```text
/recalbox/share/pixel-multiverse/
```

At runtime the daemon expects:

```text
/recalbox/share/pixel-multiverse/pm_daemon.py
/recalbox/share/pixel-multiverse/pmctl
/recalbox/share/pixel-multiverse/systems.json
/recalbox/share/pixel-multiverse/buttons.json
/tmp/es_state.inf
/tmp/pm.fifo
```

The event scripts currently call:

```text
/recalbox/share/pixel-multiverse/pmctl
```
