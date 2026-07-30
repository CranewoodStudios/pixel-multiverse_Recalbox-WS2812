#!/bin/ash
# Permanent listener reacting to ES events via the “state file”
PORT="/dev/ttyACM0"
NUM="16"

# launch a tiny Python event loop
exec python3 - <<'PY'
import os, time, threading
from pixel_multiverse import PlasmaButtons, RGBl

PORT=os.environ.get('PORT','/dev/ttyACM0')
NUM=int(os.environ.get('NUM','16'))
pb = PlasmaButtons(num_leds=NUM, serial_port_path=PORT, refresh_rate=60)

def menu_attract():
    # mild sweep in the menus
    pq=[('linear', {'direction':'left_to_right','color_on':RGBl(0,31,31,4),'color_off':RGBl(0,0,0,0),'delay':0.06})]
    pb.start_attract_mode(pq)

menu_attract()

# crude event loop: poll ES state file (lighter option is MQTT; see wiki)
state='/tmp/es_state.inf'
st_mtime=0
while True:
    try:
        m=os.path.getmtime(state)
        if m!=st_mtime:
            st_mtime=m
            d=dict([line.strip().split('=',1) for line in open(state) if '=' in line])
            action=d.get('Action','').lower()
            if action in ('rungame','rundemo'):
                pb.stop_attract_mode()
                # highlight P1 buttons solid
                for i in range(NUM): pb.set_led_mode(i,'normal', color_to=RGBl(0,31,0,8))
            elif action in ('endgame','enddemo','systembrowsing','gamelistbrowsing','start','wakeup','relaunch'):
                pb.stop_attract_mode()
                menu_attract()
    except Exception:
        pass
    time.sleep(0.2)
PY
