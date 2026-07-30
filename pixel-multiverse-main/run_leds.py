# Regenerate files with the corrected package path and module names (pixelpusher under -src)
import os, textwrap, pathlib

base = "/mnt/data"
os.makedirs(base, exist_ok=True)

run_leds_py = textwrap.dedent("""\
    #!/usr/bin/env python3
    # pixel-multiverse boot script for Picade Max (Plasma) + 7 Qanba KS RGB buttons on Recalbox
    # Repo layout uses -src/pixelpusher/*.py
    # Place this file at: /recalbox/share/pixel-multiverse/run_leds.py
    import os
    import sys
    import time
    import signal

    # Ensure we can import the local package
    PM_PATH = "/recalbox/share/pixel-multiverse/-src"
    if PM_PATH not in sys.path:
        sys.path.append(PM_PATH)

    try:
        from pixelpusher.buttons import PlasmaButtons
        from pixelpusher.colors import RGBl, C64_BLUE, C64_PINK, C64_CYAN, C64_PURPLE
    except Exception as e:
        sys.stderr.write(f"[pixel-multiverse] Failed to import library from {PM_PATH}: {e}\\n")
        sys.exit(1)

    NUM_LEDS = 7

    # Helper: pick a working serial path
    def find_serial():
        candidates = [
            "/dev/plasmabuttons",
            "/dev/ttyACM0",
            "/dev/ttyACM1",
            "/dev/ttyUSB0",
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return candidates[0]

    SERIAL_PATH = find_serial()
    sys.stderr.write(f"[pixel-multiverse] Using serial device: {SERIAL_PATH}\\n")

    # Simple 1x7 linear coord map (left to right). Adjust if your physical order differs.
    # Key is (x, y) -> index; indices are 0..6 in LED chain order.
    coord_map = { (i, 0): i for i in range(NUM_LEDS) }

    pb = PlasmaButtons(
        num_leds=NUM_LEDS,
        serial_port_path=SERIAL_PATH,
        refresh_rate=60,
        coord_map=coord_map
    )

    # Idle/attract pattern queue
    pattern_queue = [
        ('linear',   dict(direction='left_to_right',  color_on=C64_CYAN,   delay=0.03)),
        ('linear',   dict(direction='right_to_left',  color_on=C64_PINK,   delay=0.03)),
        ('circular', dict(direction='outward',        color_on=RGBl(24,24,24,6), delay=0.05)),
        ('radial',   dict(direction='clockwise',      color_on=C64_PURPLE, delay=0.03)),
    ]

    # Set a calm base color first
    pb.set_all_leds(mode="normal", color_to=C64_BLUE)

    # Start attract mode
    pb.start_attract_mode(pattern_queue)

    running = True
    def _shutdown(signum, frame):
        global running
        running = False

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    try:
        while running:
            time.sleep(0.5)
    finally:
        try:
            pb.stop_attract_mode()
        except Exception:
            pass
        try:
            pb.stop()
        except Exception:
            pass
        sys.stderr.write("[pixel-multiverse] Stopped.\\n")
    """)

custom_sh = textwrap.dedent("""\
    #!/bin/sh
    # /recalbox/share/system/custom.sh
    # Autostart pixel-multiverse LEDs on boot

    echo "[custom.sh] pixel-multiverse autostart" >> /recalbox/share/system/pixel-multiverse.log

    # Wait for USB enumeration
    sleep 5

    # If the Picade Max enumerates as ttyACM0/1, make a friendly symlink expected by the script
    if [ -e /dev/ttyACM0 ] && [ ! -e /dev/plasmabuttons ]; then
      ln -s /dev/ttyACM0 /dev/plasmabuttons
    elif [ -e /dev/ttyACM1 ] && [ ! -e /dev/plasmabuttons ]; then
      ln -s /dev/ttyACM1 /dev/plasmabuttons
    fi

    # Launch in the background so EmulationStation continues
    /usr/bin/python3 /recalbox/share/pixel-multiverse/run_leds.py >> /recalbox/share/system/pixel-multiverse.log 2>&1 &
    """)

for name, content in {"run_leds.py": run_leds_py, "custom.sh": custom_sh}.items():
    p = os.path.join(base, name)
    with open(p, "w") as f:
        f.write(content)
    os.chmod(p, 0o755)

[str(pathlib.Path(base)/"run_leds.py"), str(pathlib.Path(base)/"custom.sh")]
