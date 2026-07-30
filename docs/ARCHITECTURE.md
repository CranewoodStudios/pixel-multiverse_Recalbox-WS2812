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
4. Auto-detects a serial device, preferring `/dev/serial/by-id` entries whose
   names include Picade, Pimoroni, or Max.
5. Opens the FIFO and enters the polling loop.

The daemon handles `SIGINT` and `SIGTERM` by leaving the polling loop, sending
an all-off frame, closing the serial port, and closing the FIFO handles.

## Runtime State

The current implementation is event-driven with an idle generator rather than a
formal state machine. Events can switch the idle generator between menu and
attract patterns or run blocking transition animations before idle output
continues.

```text
startup -> menu idle
menu/game-end/attract-off -> menu idle
attract-on -> attract idle
game-start -> game-start animation -> menu idle with system accent
shutdown/reboot/off -> immediate output, then previous idle may continue
```

Known future work, such as adding a formal state machine, non-blocking
animations, persistent off/shutdown states, and serial reconnect, should be kept
as separate functional changes.

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
