# boot.py — enable USB CDC console + data
import usb_cdc
usb_cdc.enable(console=True, data=True)  # <-- critical
