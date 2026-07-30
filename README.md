# Pixel Multiverse Recalbox WS2812 Host

Host-side LED integration for a Raspberry Pi 5 running Recalbox.

This repository contains the Recalbox event hooks, LED daemon, configuration files,
and host-side tools used to send USB CDC LED frames to a compatible Picade Max
controller.

The controller firmware is maintained separately:

https://github.com/CranewoodStudios/picade-max-input-WS2812

Do not copy firmware code into this repository.

## Current Architecture

```text
Recalbox event scripts
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
External Picade Max firmware
```

## Repository Layout

```text
recalbox/
  pm_daemon.py          Main FIFO-driven LED daemon
  pmctl                 Command helper used by event scripts
  config/
    systems.json        System colours and game start layouts
    buttons.json        Button LED layout and attract patterns
  scripts/              Recalbox event hook scripts

tools/
  test_leds.py          Manual USB CDC LED test sender

docs/                   Technical documentation
archive/                Historical or uncertain files kept for reference
```

## Runtime Paths

The current runtime scripts expect deployment under:

```text
/recalbox/share/pixel-multiverse/
```

The daemon reads:

```text
/recalbox/share/pixel-multiverse/systems.json
/recalbox/share/pixel-multiverse/buttons.json
/tmp/es_state.inf
/tmp/pm.fifo
```

The Recalbox event scripts call:

```text
/recalbox/share/pixel-multiverse/pmctl
```

## Development Notes

- Keep Recalbox event hooks lightweight.
- Keep runtime behaviour stable during cleanup commits.
- Preserve user configuration during deployment.
- Keep controller firmware changes in the separate firmware repository.

More detailed documentation is being built out under `docs/`.
