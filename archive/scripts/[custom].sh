#!/bin/sh
# Autostart LED daemon (FIFO-based)
(/usr/bin/python3 /recalbox/share/pixel-multiverse/pm_daemon.py >/var/log/pm_daemon.log 2>&1 &) &
