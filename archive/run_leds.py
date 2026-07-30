#!/usr/bin/env python3
# pixel-multiverse LED control for Picade Max Plasma on Recalbox (7 LEDs)
# This variant prepends a custom site-packages path so we can install pyserial
# with:  python3 -m pip install --target /recalbox/share/pythonlibs pyserial

import os, sys, time, signal
# Add user-managed site-packages first so 'serial' (pyserial) is importable
USER_SITE = "/recalbox/share/pythonlibs"
if os.path.isdir(USER_SITE) and USER_SITE not in sys.path:
    sys.path.insert(0, USER_SITE)

REPO_ROOT = "/recalbox/share/pixel-multiverse"
CANDIDATE_SRC_DIRS = [
    os.path.join(REPO_ROOT, "src"),
    os.path.join(REPO_ROOT, "-src"),
    REPO_ROOT,
]

last_err = None
imported = False
for cand in CANDIDATE_SRC_DIRS:
    try:
        pkg_probe = os.path.join(cand, "pixelpusher", "__init__.py")
        if os.path.exists(pkg_probe):
            if cand not in sys.path:
                sys.path.insert(0, cand)
            from pixelpusher.buttons import PlasmaButtons
            from pixelpusher.colors import RGBl, C64_BLUE, C64_PINK, C64_CYAN, C64_PURPLE
            imported = True
            sys.stderr.write(f"[pixel-multiverse] Using package path: {cand}\n")
            break
    except Exception as e:
        last_err = e

if not imported:
    sys.stderr.write("[pixel-multiverse] ERROR: Could not import 'pixelpusher'.\n")
    for cand in CANDIDATE_SRC_DIRS:
        sys.stderr.write(f"   - {cand} -> {'FOUND' if os.path.exists(os.path.join(cand, 'pixelpusher', '__init__.py')) else 'missing'}\n")
    if last_err:
        sys.stderr.write(f"  Last import error: {last_err}\n")
    sys.exit(1)

NUM_LEDS = 7

def find_serial():
    candidates = ["/dev/plasmabuttons", "/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0"]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]

SERIAL_PATH = find_serial()
sys.stderr.write(f"[pixel-multiverse] Using serial device: {SERIAL_PATH}\n")

coord_map = { (i, 0): i for i in range(NUM_LEDS) }

pb = PlasmaButtons(
    num_leds=NUM_LEDS,
    serial_port_path=SERIAL_PATH,
    refresh_rate=60,
    coord_map=coord_map
)

pattern_queue = [
    ('linear',   dict(direction='left_to_right',  color_on=C64_CYAN,   delay=0.03)),
    ('linear',   dict(direction='right_to_left',  color_on=C64_PINK,   delay=0.03)),
    ('circular', dict(direction='outward',        color_on=RGBl(24,24,24,6), delay=0.05)),
    ('radial',   dict(direction='clockwise',      color_on=C64_PURPLE, delay=0.03)),
]

pb.set_all_leds(mode="normal", color_to=C64_BLUE)
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
    sys.stderr.write("[pixel-multiverse] Stopped.\n")
