#!/usr/bin/env python3
import sys, time
sys.path.insert(0, "/recalbox/share/pylibs")
sys.path.insert(0, "/recalbox/share/pixel-multiverse/src")

from pixelpusher.buttons import PlasmaButtons
from pixelpusher.colors  import RGBl

PORT="/dev/ttyACM0"
N=7

#pb = PlasmaButtons(num_leds=N, serial_port_path=PORT, refresh_rate=60)
pb = PlasmaButtons(num_leds=N, serial_port_path=PORT, refresh_rate=60, rgb_order='GRB')

def all_off():
    for i in range(N):
        pb.set_led_mode(i, 'normal', color_to=RGBl(0,0,0,0))

all_off(); time.sleep(0.1)

# Expect RED on LED 0
pb.set_led_mode(0, 'normal', color_to=RGBl(63,0,0,5))
time.sleep(2); all_off(); time.sleep(0.5)

# Expect GREEN on LED 0
pb.set_led_mode(0, 'normal', color_to=RGBl(0,63,0,5))
time.sleep(2); all_off(); time.sleep(0.5)

# Expect BLUE on LED 0
pb.set_led_mode(0, 'normal', color_to=RGBl(0,0,63,5))
time.sleep(2); all_off(); time.sleep(0.5)

pb.stop()
