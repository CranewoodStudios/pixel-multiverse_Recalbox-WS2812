#!/usr/bin/env python3
# /recalbox/share/pixel-multiverse/led_discover.py
# Discover LED indices -> button labels and auto-save to JSON.

import sys, time, json, os

# --- Adjust these if needed ---
SERIAL_PORT = "/dev/ttyACM0"
NUM_LEDS    = 7
REFRESH_HZ  = 60
SAVE_PATH   = "/recalbox/share/pixel-multiverse/button_map.json"

# Make imports work with your on-box layout
sys.path.insert(0, "/recalbox/share/pylibs")
sys.path.insert(0, "/recalbox/share/pixel-multiverse/src")

from pixelpusher.buttons import PlasmaButtons
from pixelpusher.colors  import RGBl

def all_off(pb):
    for j in range(NUM_LEDS):
        pb.set_led_mode(j, 'normal', color_to=RGBl(0,0,0,0))

def main():
    pb = PlasmaButtons(
        num_leds=NUM_LEDS,
        serial_port_path=SERIAL_PORT,
        refresh_rate=REFRESH_HZ,
    )

    # If there’s an existing map, load it (so you can add/override)
    existing = {}
    if os.path.isfile(SAVE_PATH):
        try:
            with open(SAVE_PATH, "r") as f:
                existing = json.load(f)
            if not isinstance(existing, dict):
                existing = {}
        except Exception:
            existing = {}

    print("\n--- LED Discovery ---")
    print(f"Port: {SERIAL_PORT}   LEDs: {NUM_LEDS}")
    print(f"Existing map entries loaded: {len(existing)} (from {SAVE_PATH})\n")
    print("I will light each LED in order. Type the button label (e.g., P1:A) and press ENTER.")
    print("Press ENTER with no text to skip this LED.\n")

    button_map = dict(existing)  # start from existing

    try:
        for i in range(NUM_LEDS):
            # all off
            all_off(pb)
            time.sleep(0.1)

            # current LED solid red
            pb.set_led_mode(i, 'normal', color_to=RGBl(63,0,0,15))
            print(f"[{i}/{NUM_LEDS-1}] LED index {i} is lit RED. Label? (e.g., P1:A) ", end="", flush=True)
            try:
                label = input().strip()
            except EOFError:
                label = ""

            if label:
                if label in button_map:
                    print(f"(updated {label} -> {i})")
                else:
                    print(f"(saved {label} -> {i})")
                button_map[label] = i
            else:
                print("(skipped)")

            # quick blink confirm
            pb.set_led_mode(i, 'blink',
                            color_to=RGBl(63,0,0,15),
                            color_from=RGBl(0,0,0,0),
                            transition_time=0.2)
            time.sleep(0.5)

        # end: all off
        all_off(pb)
        time.sleep(0.2)

    except KeyboardInterrupt:
        print("\nInterrupted by user.")

    finally:
        # save JSON
        try:
            os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
            with open(SAVE_PATH, "w") as f:
                json.dump(button_map, f, indent=2, sort_keys=True)
            print(f"\n✅ Saved button_map to: {SAVE_PATH}\n")
            print("Contents:\n", json.dumps(button_map, indent=2, sort_keys=True))
        except Exception as e:
            print(f"\n❌ Failed to save {SAVE_PATH}: {e}")

        pb.stop()

if __name__ == "__main__":
    main()
