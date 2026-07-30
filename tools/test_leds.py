#!/usr/bin/env python3
"""
test_leds.py — send simple frames to Plasma 2040 (MicroPython) over USB CDC.

MicroPython side: a main.py that reads stdin and looks for frames:
    b"multiverse:data" + N * (B, G, R, brightness)

Usage:
  python3 test_leds.py                 # all LEDs: red -> green -> blue -> off
  python3 test_leds.py --chase         # one-by-one chase
  python3 test_leds.py 12 --chase      # 12 LEDs, chase
"""

import os, sys, time

# Make sure pyserial installed via --target is importable
USER_SITE = "/recalbox/share/pythonlibs"
if os.path.isdir(USER_SITE) and USER_SITE not in sys.path:
    sys.path.insert(0, USER_SITE)

import serial   # pyserial

# --- CONFIG -------------------------------------------------------------
# Use the Plasma 2040 *console* interface (MicroPython stdin), typically ...-if00
PORT = "/dev/serial/by-id/usb-MicroPython_Board_in_FS_mode_e66178758b8ba831-if00"
BAUD = 115200
HEADER = b"multiverse:data"
DEFAULT_NUM_LEDS = 7
BRIGHT = 64   # 0..255
# -----------------------------------------------------------------------

def parse_args():
    num = DEFAULT_NUM_LEDS
    chase = False
    for a in sys.argv[1:]:
        if a == "--chase":
            chase = True
        else:
            try:
                num = int(a)
            except ValueError:
                print(f"Unknown argument: {a}")
                sys.exit(2)
    return num, chase

def frame_all(n, bgrb):
    """Return HEADER + payload for N LEDs all set to one color."""
    b,g,r,br = bgrb
    payload = bytearray()
    payload.extend((b,g,r,br) * n)
    return HEADER + payload

def frame_one_hot(n, index, bgrb, off=(0,0,0,0)):
    """Return HEADER + payload where only LED[index] is lit."""
    payload = bytearray()
    for i in range(n):
        if i == index:
            payload.extend(bgrb)
        else:
            payload.extend(off)
    return HEADER + payload

def main():
    n, chase = parse_args()

    if not os.path.exists(PORT):
        print(f"ERROR: Port not found: {PORT}")
        print("Hint: run  ls -l /dev/serial/by-id/  and update PORT.")
        sys.exit(1)

    print(f"[test_leds] Using {PORT} @ {BAUD} for {n} LEDs")
    with serial.Serial(PORT, BAUD, timeout=0.2) as ser:
        if chase:
            print("[test_leds] Chase…")
            on = (0, 0, 255, BRIGHT)  # red (B,G,R,brightness)
            for i in range(n):
                ser.write(frame_one_hot(n, i, on))
                ser.flush()
                time.sleep(0.20)
            # off
            ser.write(frame_all(n, (0,0,0,0)))
            ser.flush()
            print("[test_leds] Done.")
        else:
            steps = [
                (0, 0, 255, BRIGHT),  # red
                (0, 255, 0, BRIGHT),  # green
                (255, 0, 0, BRIGHT),  # blue
                (0, 0, 0, 0),         # off
            ]
            print("[test_leds] Cycle: red -> green -> blue -> off")
            for s in steps:
                ser.write(frame_all(n, s))
                ser.flush()
                print("  sent", s)
                time.sleep(2.0)
            print("[test_leds] Done.")

if __name__ == "__main__":
    main()
