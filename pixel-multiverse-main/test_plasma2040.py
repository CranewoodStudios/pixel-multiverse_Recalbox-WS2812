#!/usr/bin/env python3
"""
Test script for Pimoroni Plasma 2040 running code.py (multiverse:data bridge).
Cycles all LEDs: red → green → blue → off.
"""

import os, sys, time
import serial  # needs pyserial (installed into /recalbox/share/pythonlibs)

# === Adjust this if needed ===
CANDIDATES = [
    "/dev/serial/by-id/usb-Adafruit_CircuitPython_Plasma2040*",  # generic by-id
    "/dev/ttyACM0",
    "/dev/ttyACM1",
]
NUM_LEDS = 7  # set to total LEDs in your chain (buttons + any strips)
BAUD = 115200
HEADER = b"multiverse:data"
# =============================

def pick_port():
    for p in CANDIDATES:
        # expand wildcards
        if "*" in p:
            import glob
            for path in glob.glob(p):
                return path
        if os.path.exists(p):
            return p
    return None

def make_frame(color):
    """color = (b,g,r,brightness). Returns HEADER+payload."""
    payload = bytearray()
    for _ in range(NUM_LEDS):
        b,g,r,br = color
        payload += bytes((b,g,r,br))
    return HEADER + payload

def main():
    port = pick_port()
    if not port:
        print("No Plasma 2040 serial device found.")
        sys.exit(1)
    print(f"Using {port}")
    ser = serial.Serial(port, BAUD, timeout=0.1)

    colors = [
        (0,0,255,64),   # red
        (0,255,0,64),   # green
        (255,0,0,64),   # blue
        (0,0,0,0),      # off
    ]

    for c in colors:
        frame = make_frame(c)
        ser.write(frame)
        ser.flush()
        print("Sent", c)
        time.sleep(2)

    ser.close()
    print("Done.")

if __name__ == "__main__":
    main()
