# USB Protocol

The host daemon sends binary USB CDC frames to the controller.

Current frame shape:

```text
b"multiverse:data" + N * (B, G, R, brightness)
```

Detailed framing and compatibility notes should be maintained here without
duplicating controller firmware implementation details.
