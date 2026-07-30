# Picade Integration

This repository contains only the Recalbox host-side LED system.

Compatible controller firmware is maintained separately:

https://github.com/CranewoodStudios/picade-max-input-WS2812

Host and firmware communicate through a shared USB CDC protocol.

The firmware repository is responsible for:

- RP2040 firmware
- USB HID devices
- USB CDC receiver
- WS2812 output
- PIO implementation details

This repository is responsible for:

- Recalbox and EmulationStation event integration
- Host-side LED animation generation
- Game and system colour mapping
- Button layout configuration
- USB CDC writes to the compatible controller
- Recalbox deployment tooling

Do not copy firmware source into this repository. Protocol changes should be
documented in `docs/USB_PROTOCOL.md` and coordinated with the firmware project.

Pixel Multiverse is maintained by CranewoodStudios and distributed under the MIT
License. See `LICENSE`.
