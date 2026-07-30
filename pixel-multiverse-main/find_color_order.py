#!/usr/bin/env python3
# /recalbox/share/pixel-multiverse/find_color_order.py
import sys, time, json, os
sys.path.insert(0,"/recalbox/share/pylibs")
sys.path.insert(0,"/recalbox/share/pixel-multiverse/src")

from pixelpusher.buttons import PlasmaButtons
from pixelpusher.colors  import RGBl

PORT="/dev/ttyACM0"
N=7
ORDERS = ["GRB","RGB","BRG"]  # most WS2812 are GRB

def all_off(pb):
  for i in range(N):
    pb.set_led_mode(i,'normal',color_to=RGBl(0,0,0,0))

best=None
for order in ORDERS:
  try:
    pb = PlasmaButtons(num_leds=N, serial_port_path=PORT, refresh_rate=60, color_order=order)
  except TypeError as e:
    print(f"(constructor doesn’t accept color_order? {e})")
    sys.exit(1)

  print(f"\nTesting order: {order}")
  all_off(pb); time.sleep(0.2)
  pb.set_led_mode(0,'normal',RGBl(63,0,0,10)); print("  Expect: RED");   time.sleep(1.2)
  pb.set_led_mode(0,'normal',RGBl(0,63,0,10)); print("  Expect: GREEN"); time.sleep(1.2)
  pb.set_led_mode(0,'normal',RGBl(0,0,63,10)); print("  Expect: BLUE");  time.sleep(1.2)
  all_off(pb); pb.stop()

  ans = input(f"Did that look like RED→GREEN→BLUE for {order}? [y/N] ").strip().lower()
  if ans == "y":
    best = order
    break

if best:
  cfg = {"color_order": best}
  os.makedirs("/recalbox/share/pixel-multiverse", exist_ok=True)
  with open("/recalbox/share/pixel-multiverse/led_config.json","w") as f:
    json.dump(cfg, f, indent=2)
  print(f"\nSaved /recalbox/share/pixel-multiverse/led_config.json with {cfg}")
else:
  print("\nNo order confirmed—rerun and pick the one that shows proper colors.")
