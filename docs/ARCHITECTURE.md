# Architecture

This document will become the primary technical reference for the host-side
Recalbox LED system.

Current flow:

```text
Recalbox event scripts -> pmctl -> /tmp/pm.fifo -> pm_daemon.py -> USB CDC
```

The compatible Picade Max firmware is a separate project.
