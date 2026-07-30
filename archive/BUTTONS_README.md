# Button LED Configuration

## Overview

The `pm_daemon.py` now supports YAML-based button LED configuration with customizable attract mode patterns. This allows you to:

- Define LED coordinate mappings
- Configure attract mode patterns (linear, radial, circular)
- Customize colors, directions, and timing for each pattern

## Configuration File

Create a `buttons.yml` file at `/recalbox/share/pixel-multiverse/buttons.yml` (or configure `BUTTONS_YAML` in `pm_daemon.py`).

### Basic Structure

```yaml
buttons:
  enabled: true
  num_leds: 30              # Total number of LEDs
  refresh_rate: 60          # Refresh rate in Hz
  
  led_map:                  # Map coordinates to LED indices
    - coord: [x, y]
      value: led_index
    # ... more mappings
  
  attract_program:          # Patterns for attract mode
    - pattern: linear       # Pattern type
      params:
        direction: left_to_right
        color_on: [b, g, r, br]
        color_off: [b, g, r, br]
        delay: 0.05
    # ... more patterns
```

## LED Mapping (`led_map`)

Maps physical LED positions (x, y coordinates) to LED indices:

```yaml
led_map:
  - coord: [0, 0]    # Top-left position
    value: 0         # LED index 0
  - coord: [1, 0]
    value: 1
  # ... continue for all LEDs
```

**Note:** Coordinates should reflect your physical button layout. For example, if you have buttons arranged in a 5x6 grid, use coordinates from [0,0] to [4,5].

## Attract Patterns

### Pattern Types

1. **linear** - Sweep patterns in straight lines
   - Directions: `left_to_right`, `right_to_left`, `top_to_bottom`, `bottom_to_top`

2. **radial** - Rotational patterns around center
   - Directions: `clockwise`, `anticlockwise`

3. **circular** - Expanding/contracting patterns from center
   - Directions: `outward`, `inward`

### Pattern Parameters

- `direction`: Pattern direction (see above for each type)
- `color_on`: BGRBR tuple `[blue, green, red, brightness]` (0-255 each)
- `color_off`: BGRBR tuple for "off" state (optional, defaults to black)
- `delay`: Time in seconds between animation steps

### Example Patterns

```yaml
attract_program:
  # Sweep from left to right in blue
  - pattern: linear
    params:
      direction: left_to_right
      color_on: [255, 0, 0, 40]      # Blue
      color_off: [0, 0, 0, 0]        # Off
      delay: 0.05

  # Clockwise rotation in yellow
  - pattern: radial
    params:
      direction: clockwise
      color_on: [0, 255, 255, 40]    # Yellow (G+R)
      color_off: [0, 0, 0, 0]
      delay: 0.05

  # Expand outward in purple
  - pattern: circular
    params:
      direction: outward
      color_on: [255, 0, 255, 40]    # Purple (B+R)
      color_off: [0, 0, 0, 0]
      delay: 0.05
```

## Color Format

Colors use BGRBR format (Blue, Green, Red, Brightness):
- Values range from 0-255
- Brightness is typically 0-40 for LEDs (hardware dependent)
- Examples:
  - Red: `[0, 0, 255, 40]`
  - Green: `[0, 255, 0, 40]`
  - Blue: `[255, 0, 0, 40]`
  - Yellow: `[0, 255, 255, 40]`
  - Purple: `[255, 0, 255, 40]`
  - Cyan: `[255, 255, 0, 40]`
  - White: `[255, 255, 255, 40]`

## Backward Compatibility

If `buttons.yml` is not found or YAML is not available:
- Falls back to hardcoded "breath" or "rainbow" modes
- Uses existing `NUM_LEDS` configuration from `pm_daemon.py`
- All event handling continues to work normally

## Reloading Configuration

Send a `reload-config` event to reload both `systems.json` and `buttons.yml`:

```bash
echo '{"event":"reload-config"}' > /tmp/pm.fifo
```

## Troubleshooting

Check daemon logs for configuration messages:
- "loaded buttons.yml: X LEDs mapped, Y patterns" - Success
- "yaml not available, skipping buttons config" - PyYAML not installed
- "buttons.yml not found at..." - Configuration file missing
- "buttons.yml not loaded: ..." - Parse error in YAML file

### Installing PyYAML

If PyYAML is not available:
```bash
pip3 install PyYAML
# or
pip3 install --target /recalbox/share/pythonlibs PyYAML
```
