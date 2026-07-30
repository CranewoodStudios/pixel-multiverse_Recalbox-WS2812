# AGENTS.md

## Purpose

This document provides context for AI coding assistants (ChatGPT, Codex, Claude Code, etc.) working on this repository.

Read this document before making changes.

---

# Project Scope

This repository contains the **host-side LED system** for a Raspberry Pi 5 running Recalbox.

It is responsible for:

- Recalbox and EmulationStation event integration
- LED animation generation
- Game/system colour mapping
- Button layout configuration
- USB communication with a compatible controller
- Installation and deployment on Recalbox

This repository **does not** contain controller firmware.

# Related Project

The compatible controller firmware is maintained in a separate repository:

https://github.com/CranewoodStudios/picade-max-input-WS2812

That project is responsible for the RP2040 firmware, USB HID devices, USB CDC interface and WS2812 output.

The two repositories communicate through a shared USB protocol but remain independent projects.

Do not copy firmware code into this repository.

---

# Architecture

```text
Recalbox Event Scripts
        │
        ▼
      pmctl
        │
        ▼
   /tmp/pm.fifo
        │
        ▼
   pm_daemon.py
        │
        │ USB CDC
        ▼

====================================

External Picade Max Firmware Project

USB CDC Receiver
        │
        ▼
RP2040 PIO
        │
        ▼
WS2812 LEDs
```

---

# Current Priorities

1. Clean and organise the repository.
2. Preserve runtime behaviour.
3. Improve documentation.
4. Only after cleanup, begin functional improvements.

---

# Target Repository Layout

```text
README.md
AGENTS.md
LICENSE

recalbox/
    pm_daemon.py
    pmctl
    config/
    scripts/

tools/

docs/
    ARCHITECTURE.md
    USB_PROTOCOL.md
    CONFIGURATION.md
    INSTALLATION.md
    DEVELOPMENT.md
    PICADE_INTEGRATION.md

archive/
```

---

# Documentation Roadmap

AGENTS.md should remain a concise orientation document.

As the project matures, detailed implementation information should move into the `docs/` directory.

## docs/ARCHITECTURE.md

This should become the primary technical reference.

It should document:

- overall architecture
- component responsibilities
- event flow
- daemon lifecycle
- daemon state machine
- startup/shutdown
- serial communication
- deployment architecture

It should include:

- component diagrams
- sequence diagrams
- state diagrams
- data flow diagrams

## docs/USB_PROTOCOL.md

Describe the USB CDC protocol used by the host.

## docs/CONFIGURATION.md

Document buttons.json and systems.json.

## docs/INSTALLATION.md

Installation and deployment onto Recalbox.

## docs/DEVELOPMENT.md

Developer workflow, testing and debugging.

## docs/PICADE_INTEGRATION.md

Describe compatibility with the separate firmware project without duplicating firmware documentation.

Documentation philosophy:

- README.md explains what the project is.
- AGENTS.md explains how contributors and AI agents should work.
- docs/ explains how the software works.

Whenever AGENTS.md grows too detailed, move the information into docs/ and leave a summary.

---

# Known Technical Improvements

After cleanup:

- Rebuild ORDER after NUM_LEDS changes.
- Make animations non-blocking.
- Add serial reconnect.
- Introduce daemon state machine.
- Make OFF and SHUTDOWN persistent.
- Improve USB framing in coordination with the firmware repository.

---

# Development Rules

- Keep Recalbox event hooks lightweight.
- Use git mv during cleanup.
- Separate cleanup commits from functional changes.
- Treat the Raspberry Pi as the deployment target and the desktop as the development environment.
- Preserve user configuration during deployment.
- Keep dependencies minimal.

---

# AI Workflow

1. Read AGENTS.md.
2. Read README.md.
3. Read docs/ARCHITECTURE.md (when available).
4. Create a feature branch.
5. Keep commits small and focused.
6. Do not mix repository cleanup with behavioural changes.
7. Archive uncertain files instead of deleting them.
