# USB Protocol

The host daemon sends binary USB CDC frames to the controller.

Current frame shape:

```text
b"multiverse:data" + N * (B, G, R, brightness)
```

The header is the ASCII byte sequence:

```text
multiverse:data
```

Each LED contributes four bytes after the header:

```text
B G R brightness
```

For `N` LEDs, the payload after the header is `N * 4` bytes.

## Serial Transport

The daemon opens the selected USB CDC serial device at 115200 baud with a short
timeout. `PM_PORT` can override auto-detection when it points to an existing
device path.

When `PM_PORT` is set, the daemon keeps attempting that path on each
rate-limited reconnect attempt. It does not permanently abandon the override
because the device was absent or could not be opened once.

Auto-detection currently checks `/dev/serial/by-id` for names containing
Picade, Pimoroni, or Max, then falls back to `/dev/ttyACM0` and
`/dev/ttyACM1`.

The daemon does not require USB to be present at startup. If the serial device
is missing or a write fails, the daemon closes the current connection, keeps
processing FIFO commands, retries discovery on a short rate-limited interval,
and resends the latest intended LED frame after reconnecting.

## Compatibility Boundary

This document describes only the host-side bytes sent by this repository. The
receiver, RP2040 PIO code, USB HID devices, and WS2812 output implementation
belong to the separate Picade Max firmware repository.

Future protocol changes should be coordinated with that repository and should
not be hidden inside cleanup commits.
