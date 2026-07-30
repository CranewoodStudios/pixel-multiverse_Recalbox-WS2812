# Pixel Multiverse Recalbox WS2812 Host

Host-side LED integration for a Raspberry Pi 5 running Recalbox.

This repository contains the Recalbox event hooks, LED daemon, configuration files,
and host-side tools used to send USB CDC LED frames to a compatible Picade Max
controller.

The controller firmware is maintained separately:

https://github.com/CranewoodStudios/picade-max-input-WS2812

Do not copy firmware code into this repository.

Pixel Multiverse is maintained by CranewoodStudios and is distributed under the
MIT License. See `LICENSE` for details.

## Features

- Recalbox and EmulationStation event integration
- FIFO-based command delivery from lightweight shell hooks to the daemon
- Game and system colour mapping through JSON configuration
- Button LED layout configuration and attract animation patterns
- USB CDC frame output for a compatible Picade Max controller
- Minimal host-side dependencies for the Recalbox target

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

## Documentation

- `docs/ARCHITECTURE.md` describes the host-side components and event flow.
- `docs/INSTALLATION.md` describes Recalbox deployment.
- `docs/CONFIGURATION.md` describes `buttons.json` and `systems.json`.
- `docs/USB_PROTOCOL.md` describes the host USB CDC frame format.
- `docs/DEVELOPMENT.md` describes desktop development and checks.
- `docs/PICADE_INTEGRATION.md` describes the external firmware relationship.

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

## Support

- Issues: https://github.com/CranewoodStudios/pixel-multiverse_Recalbox-WS2812/issues
- Discussions: https://github.com/CranewoodStudios/pixel-multiverse_Recalbox-WS2812/discussions

## Attribution

Pixel Multiverse was created and is maintained by CranewoodStudios.
