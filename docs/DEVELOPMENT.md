# Development

The desktop environment is used for repository cleanup, editing, and static
checks. The Raspberry Pi running Recalbox is the deployment target.

Keep cleanup, documentation, and functional changes in separate commits.

## Workflow

1. Read `AGENTS.md`.
2. Keep Recalbox event hooks lightweight.
3. Preserve runtime behaviour during cleanup work.
4. Do not mix repository reorganisation with daemon behaviour changes.
5. Archive uncertain historical files instead of deleting them.
6. Treat deployed `buttons.json` and `systems.json` as user configuration.

## Static Checks

Run shell syntax checks for deployment and event scripts:

```sh
sh -n tools/deploy_recalbox.sh
sh -n recalbox/pmctl
sh -n recalbox/scripts/*.sh
```

Run Python syntax checks:

```sh
python3 -m py_compile recalbox/pm_daemon.py tools/test_leds.py
```

Run unit tests when daemon behavior changes:

```sh
python3 -m unittest discover tests
```

## Manual Runtime Checks

On Recalbox, after deployment and daemon startup:

```sh
sh /recalbox/share/pixel-multiverse/pmctl menu
sh /recalbox/share/pixel-multiverse/pmctl game-start
sh /recalbox/share/pixel-multiverse/pmctl attract-on
sh /recalbox/share/pixel-multiverse/pmctl off
```

USB reconnect checks should include daemon startup without the controller
connected, issuing commands while disconnected, reconnecting or resetting the
controller, and confirming the latest LED state is sent after reconnect.

For verbose daemon diagnostics during development:

```sh
PM_LOG_LEVEL=DEBUG /usr/bin/python3 recalbox/pm_daemon.py
```

Manual USB CDC frame testing is available through:

```sh
tools/test_leds.py
```

## Known Future Functional Work

Do not fold these into cleanup commits:

- Rebuild `ORDER` after `NUM_LEDS` changes.
- Make animations non-blocking.
- Add serial reconnect.
- Introduce an explicit daemon state machine.
- Make `off` and `shutdown` persistent states.
- Improve USB framing in coordination with the firmware repository.

## Project Metadata

Pixel Multiverse is maintained by CranewoodStudios and distributed under the MIT
License. See `LICENSE`.
