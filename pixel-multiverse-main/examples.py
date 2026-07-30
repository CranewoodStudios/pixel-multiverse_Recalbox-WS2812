from src.pixelpusher import *
import time



time.sleep(5)

# Display the PNG with rescaling and a background color (for transparency)



# Define a button map
button_map = {'P1:START': 0, 'P1:A': 1, 'P1:B': 2, 'P1:X': 3, 'P1:Y': 4, 'P1:L1': 5, 'P1:L2': 6,
              }

# Define a coordinate map
coord_map = {
    (68, 14): 0, (65, 12): 1, (63, 15): 2, (66, 17): 3, (67, 7): 4, (64, 5): 5, (62, 8): 6,
}

num_leds = 7
refresh_rate = 60
serial_port = "/dev/ttyACM0"

# Initialize the PlasmaButtons object with the button map and coordinate map
plasma_buttons = PlasmaButtons(num_leds, serial_port, refresh_rate, button_map, coord_map)


# Set LED modes using button labels
plasma_buttons.set_button_mode(0, 'blink', color_to=RGBl(0, 63, 0, 15), color_from=RGBl(0, 0, 0, 0), transition_time=0.25)
plasma_buttons.set_button_mode(1, 'blink', color_to=RGBl(0, 0, 63, 15), color_from=RGBl(0, 0, 0, 0), transition_time=0.25)
plasma_buttons.set_button_mode(2, 'blink', color_to=RGBl(63, 0, 0, 15), color_from=RGBl(0, 0, 0, 0), transition_time=0.25)
plasma_buttons.set_button_mode(3, 'blink', color_to=RGBl(63, 63, 0, 15), color_from=RGBl(0, 0, 0, 0), transition_time=0.25)
plasma_buttons.set_button_mode(4, 'blink', color_to=RGBl(0, 63, 63, 15), color_from=RGBl(0, 0, 0, 0), transition_time=0.25)
plasma_buttons.set_button_mode(5, 'blink', color_to=RGBl(63, 0, 63, 15), color_from=RGBl(0, 0, 0, 0), transition_time=0.25)
plasma_buttons.set_button_mode(6, 'blink', color_to=RGBl(63, 63, 63, 15), color_from=RGBl(0, 0, 0, 0), transition_time=0.25)



time.sleep(3)

plasma_buttons.set_button_mode(0, 'normal', color_to=RGBl(0, 63, 0, 15))
plasma_buttons.set_button_mode(1, 'normal', color_to=RGBl(0, 0, 63, 15))
plasma_buttons.set_button_mode(2, 'normal', color_to=RGBl(63, 0, 0, 15))
plasma_buttons.set_button_mode(3, 'normal', color_to=RGBl(63, 63, 0, 15))
plasma_buttons.set_button_mode(4, 'normal', color_to=RGBl(0, 63, 63, 15))
plasma_buttons.set_button_mode(5, 'normal', color_to=RGBl(63, 0, 63, 15))
plasma_buttons.set_button_mode(6, 'normal', color_to=RGBl(63, 63, 63, 15))



time.sleep(3)

plasma_buttons.set_button_mode(0, 'fade', color_to=RGBl(10, 10, 10, 5), transition_time=2)
plasma_buttons.set_button_mode(1, 'fade', color_to=RGBl(10, 10, 10, 5), transition_time=2)
plasma_buttons.set_button_mode(2, 'fade', color_to=RGBl(10, 10, 10, 5), transition_time=2)
plasma_buttons.set_button_mode(3, 'fade', color_to=RGBl(10, 10, 10, 5), transition_time=2)
plasma_buttons.set_button_mode(4, 'fade', color_to=RGBl(10, 10, 10, 5), transition_time=2)
plasma_buttons.set_button_mode(5, 'fade', color_to=RGBl(10, 10, 10, 5), transition_time=2)
plasma_buttons.set_button_mode(6, 'fade', color_to=RGBl(10, 10, 10, 5), transition_time=2)



# Allow the program to run for a while before stopping (example)
time.sleep(5)

# Display the PNG without rescaling and no background color (uses existing frame buffer)


x_values = sorted(set(coord[0] for coord in coord_map.keys()))
y_values = sorted(set(coord[1] for coord in coord_map.keys()))

# Calculate the full range of x values, including those without LEDs
min_x, max_x = min(x_values), max(x_values)+1
min_y, max_y = min(y_values), max(y_values)+1

for _ in range(1, 2):
    for column in range (min_x, max_x):
        for row in range (min_y, max_y):
            plasma_buttons.set_led_mode_by_coord(coord=(column, row),mode="normal", color_to=RGBl(31, 31, 31, 5))
        time.sleep(0.01)
    for column in range(min_x, max_x):
        for row in range (min_y, max_y):
            plasma_buttons.set_led_mode_by_coord(coord=(column, row),mode="normal", color_to=RGBl(15, 15, 0, 5))
        time.sleep(0.01)
    time.sleep(0.2)

for _ in range(1, 3):
    for row in range (min_y, max_y):
        for column in range (min_x, max_x):
            plasma_buttons.set_led_mode_by_coord(coord=(column, row),mode="normal", color_to=RGBl(31, 31, 31, 5))
        time.sleep(0.01)
    for row in range (min_y, max_y):
        for column in range (min_x, max_x):
            plasma_buttons.set_led_mode_by_coord(coord=(column, row),mode="normal", color_to=RGBl(0, 15, 15, 5))
        time.sleep(0.01)
    time.sleep(0.2)

for _ in range(1, 2):
    for column in range (max_x, min_x, -1):
        for row in range (min_y, max_y):
            plasma_buttons.set_led_mode_by_coord(coord=(column, row),mode="normal", color_to=RGBl(31, 31, 31, 5))
        time.sleep(0.01)
    for column in range(max_x, min_x, -1):
        for row in range (min_y, max_y):
            plasma_buttons.set_led_mode_by_coord(coord=(column, row),mode="normal", color_to=RGBl(15, 0, 15, 5))
        time.sleep(0.01)
    time.sleep(0.2)

for _ in range(1, 3):
    for row in range (max_y, min_y, -1):
        for column in range (min_x, max_x):
            plasma_buttons.set_led_mode_by_coord(coord=(column, row),mode="normal", color_to=RGBl(31, 31, 31, 5))
        time.sleep(0.01)
    for row in range (max_y, min_y, -1):
        for column in range (min_x, max_x):
            plasma_buttons.set_led_mode_by_coord(coord=(column, row),mode="normal", color_to=RGBl(0, 0, 0, 5))
        time.sleep(0.01)
    time.sleep(0.2)



plasma_buttons.set_button_mode_by_label(button_label="P1:A", mode="fade sweep", color_from=RGBl(0,63,63,15),
                                        color_to=RGBl(0,0,63,15), transition_time=0.5)
plasma_buttons.set_button_mode_by_label(button_label="P1:B", mode="normal", color_to=RGBl(15,15,63,15))
plasma_buttons.set_button_mode_by_label(button_label="P1:X", mode="normal", color_to=RGBl(15,15,63,15))
plasma_buttons.set_button_mode_by_label(button_label="P1:Y", mode="normal", color_to=RGBl(15,15,63,15))
plasma_buttons.set_button_mode_by_label(button_label="P1:L1", mode="normal", color_to=RGBl(15,15,63,15))
plasma_buttons.set_button_mode_by_label(button_label="P1:R1", mode="normal", color_to=RGBl(15,15,63,15))
plasma_buttons.set_button_mode_by_label(button_label="P1:SELECT", mode="blink", color_from=RGBl(31,31,63,15),
                                        color_to=RGBl(5,5,63,15),transition_time=0.5)

plasma_buttons.set_button_mode_by_label(button_label="P2:A", mode="fade sweep", color_from=RGBl(63,63,0,15),
                                        color_to=RGBl(63,0,0,15), transition_time=0.5)
plasma_buttons.set_button_mode_by_label(button_label="P2:B", mode="normal", color_to=RGBl(63,15,15,15))
plasma_buttons.set_button_mode_by_label(button_label="P2:X", mode="normal", color_to=RGBl(63,15,15,15))
plasma_buttons.set_button_mode_by_label(button_label="P2:Y", mode="normal", color_to=RGBl(63,15,15,15))
plasma_buttons.set_button_mode_by_label(button_label="P2:L1", mode="normal", color_to=RGBl(63,15,15,15))
plasma_buttons.set_button_mode_by_label(button_label="P2:R1", mode="normal", color_to=RGBl(63,15,15,15))
plasma_buttons.set_button_mode_by_label(button_label="P2:SELECT", mode="blink", color_from=RGBl(63,31,31,15),
                                        color_to=RGBl(63,5,5,15),transition_time=0.5)

time.sleep(5)

plasma_buttons.set_button_mode(0, 'fade', color_to=RGBl(0, 0, 0, 0), transition_time=2)
plasma_buttons.set_button_mode(1, 'fade', color_to=RGBl(0, 0, 0, 0), transition_time=2)
plasma_buttons.set_button_mode(2, 'fade', color_to=RGBl(0, 0, 0, 0), transition_time=2)
plasma_buttons.set_button_mode(3, 'fade', color_to=RGBl(0, 0, 0, 0), transition_time=2)
plasma_buttons.set_button_mode(4, 'fade', color_to=RGBl(0, 0, 0, 0), transition_time=2)
plasma_buttons.set_button_mode(5, 'fade', color_to=RGBl(0, 0, 0, 0), transition_time=2)
plasma_buttons.set_button_mode(6, 'fade', color_to=RGBl(0, 0, 0, 0), transition_time=2)



time.sleep(3)

plasma_buttons.stop()

