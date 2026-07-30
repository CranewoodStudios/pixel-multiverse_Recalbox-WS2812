# Installation

Installation should deploy files from `recalbox/` into the paths expected by the
runtime scripts on Recalbox.

Current expected application directory:

```text
/recalbox/share/pixel-multiverse/
```

The runtime layout is flattened. Files from `recalbox/config/` are deployed as
top-level JSON files beside `pm_daemon.py` and `pmctl`.

## Deploy Runtime Files

From the repository root on the Recalbox target:

```sh
tools/deploy_recalbox.sh
```

The script copies:

```text
recalbox/pm_daemon.py        -> /recalbox/share/pixel-multiverse/pm_daemon.py
recalbox/pmctl               -> /recalbox/share/pixel-multiverse/pmctl
recalbox/config/buttons.json -> /recalbox/share/pixel-multiverse/buttons.json
recalbox/config/systems.json -> /recalbox/share/pixel-multiverse/systems.json
recalbox/scripts/*.sh        -> /recalbox/share/pixel-multiverse/*.sh
```

Existing runtime `buttons.json` and `systems.json` are preserved by default. If
either file already exists, the script writes a timestamped backup and leaves
the existing file in place.

To replace existing configuration after creating backups:

```sh
tools/deploy_recalbox.sh --force-config
```

To preview without copying:

```sh
tools/deploy_recalbox.sh --dry-run
```

For testing outside Recalbox, use a different target:

```sh
tools/deploy_recalbox.sh --target /tmp/pixel-multiverse-runtime
```

## Autostart

`recalbox/scripts/custom.sh` starts the daemon with:

```sh
/usr/bin/python3 /recalbox/share/pixel-multiverse/pm_daemon.py
```

and redirects daemon output to:

```text
/var/log/pm_daemon.log
```

Current expected event script installation depends on the Recalbox event hook
location used by the target system. The scripts themselves are kept lightweight
and call `/recalbox/share/pixel-multiverse/pmctl`.

## Dependencies

The daemon requires Python 3 and `pyserial`. It prepends this path when present:

```text
/recalbox/share/pythonlibs
```

Install target dependencies in a way that preserves Recalbox system files and
keeps host-side dependencies minimal.

## Troubleshooting

If LEDs do not respond:

- Confirm the compatible Picade Max controller is connected.
- Confirm the firmware exposes a USB CDC serial device.
- Check `/var/log/pm_daemon.log`.
- Look for `USB reconnect`, `USB connected`, or `USB disconnected` messages.
- Confirm `/tmp/pm.fifo` exists after daemon startup.
- Run `sh /recalbox/share/pixel-multiverse/pmctl menu` and check for FIFO
  errors.
- Use `PM_PORT=/dev/ttyACM0` or another device path to test serial detection.

If configuration changes do not appear:

- Validate JSON syntax before deployment.
- Confirm the deployed files are in `/recalbox/share/pixel-multiverse/`.
- Send `reload-config` through `pmctl` or restart the daemon.
