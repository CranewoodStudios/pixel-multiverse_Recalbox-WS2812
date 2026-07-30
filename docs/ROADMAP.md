# Roadmap

This document tracks future Pixel Multiverse host-side work without adding
speculative implementation code.

## Phase 3: USB Protocol Version 2

Do not begin protocol implementation until Phase 2 reliability work has been
merged and tested on real Raspberry Pi 5 and RP2040 hardware.

Protocol version 2 affects both repositories:

- Host repository: `CranewoodStudios/pixel-multiverse_Recalbox-WS2812`
- Firmware repository: `CranewoodStudios/picade-max-input-WS2812`

Before code changes, write and approve a protocol design covering magic bytes,
protocol version, message types, payload length, sequence number, payload byte
order, checksum or CRC, maximum payload size, partial reads, malformed frames,
resynchronization, optional capability negotiation, and backward compatibility.

## Future Features

| Feature | User value | Dependencies | Risks | Repository | Likely phase |
| --- | --- | --- | --- | --- | --- |
| Attract mode | More engaging idle cabinet lighting. | Stable non-blocking animation loop and config reload. | Can distract from menu state or mask sleep/off behavior. | Host | Phase 4 |
| Layered animations | Combine base state, highlights, and temporary effects. | Explicit state machine and non-blocking animation scheduling. | Can grow into an oversized animation framework. | Host | Phase 4 |
| LED profiles | Switch layouts for cabinet variants or user preferences. | Atomic config loading and preserved deployed user config. | Incorrect profile selection can remap buttons unexpectedly. | Host | Phase 4 |
| Themes | User-selectable color sets for systems and menus. | LED profiles and live config reload. | Theme format can duplicate `systems.json` if not designed carefully. | Host | Phase 4 |
| Diagnostics command | Let operators request daemon status from `pmctl`. | Structured logging and explicit daemon state. | FIFO is currently one-way, so response transport needs design. | Host | Phase 4 |
| Hardware status command | Report USB connection and firmware status. | Protocol v2 or another response mechanism. | Requires firmware coordination and robust timeout behavior. | Both | After Phase 3 |
| Network API | Remote control or monitoring over the local network. | Diagnostics model and security design. | Expands attack surface and Recalbox runtime complexity. | Host | Later |
| Web configuration UI | Easier editing of systems, buttons, and themes. | Config schema, validation, and deployment story. | Adds frontend/runtime dependencies to a minimal target. | Host | Later |
| Release packaging | Repeatable versioned deployment artifacts. | Stable layout and install/update scripts. | Packaging can overwrite user config if not careful. | Host | Phase 4 |
| Remote deployment helper | Push runtime files from development Pi to Recalbox Pi. | Deployment script and target path detection. | Network/auth differences across Recalbox installs. | Host | Phase 4 |
| Installer and uninstaller | Safer first install and clean removal. | Stable deployment paths and service/startup model. | Must preserve user config and avoid damaging Recalbox hooks. | Host | Phase 4 |
| Firmware update tooling | Simplify compatible controller updates. | Firmware release process and protocol compatibility metadata. | Cross-repository coordination and hardware recovery risk. | Both | Later |
