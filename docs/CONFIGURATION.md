# Configuration

Runtime configuration is currently deployed to:

```text
/recalbox/share/pixel-multiverse/systems.json
/recalbox/share/pixel-multiverse/buttons.json
```

Repository source copies live under:

```text
recalbox/config/
```

`systems.json` defines default menu colours, system accents, start layouts, and
ROM-specific overrides.

`buttons.json` defines button LED count, coordinate mapping, and attract mode
patterns.

The deployed copies are user configuration. Deployment must preserve existing
runtime `buttons.json` and `systems.json` unless the operator explicitly chooses
to replace them after backup.

## Colour Format

The daemon internally sends colours as:

```text
(B, G, R, brightness)
```

JSON colour objects use named `b`, `g`, `r`, and `br` fields. Hex strings in
`start_layout` use normal `#rrggbb:brightness` notation and are converted by the
daemon before transmission.

Brightness is clamped by the daemon's configured brightness limit.

## systems.json

Top-level keys are system IDs such as `snes`, `nes`, `mame`, and `psx`.

`defaults.menu_color` defines the fallback menu idle colour.

`defaults.attract` selects the fallback attract mode when no button pattern
program is available.

Each system can define:

- `accent`: system colour as `{ "b": 0, "g": 0, "r": 255, "br": 36 }`
- `start_layout`: per-LED colours used on game start
- `rom_overrides`: ROM-name-specific settings, keyed by ROM filename without
  extension

Example:

```json
{
  "snes": {
    "accent": { "b": 0, "g": 0, "r": 255, "br": 36 },
    "start_layout": ["#ff0000:100", "#ffffff:100"],
    "rom_overrides": {
      "Super Mario World": {
        "start_layout": ["#00ff00:100", "#ffffff:100"]
      }
    }
  }
}
```

## buttons.json

`buttons.enabled` allows the daemon to use button-specific configuration.

`buttons.num_leds` updates the daemon's LED count during configuration load.
The current implementation does not rebuild the physical `ORDER` list after
this value changes; that is a known future functional improvement.

`buttons.led_map` maps logical two-dimensional button coordinates to LED
indexes:

```json
{ "coord": [0, 0], "value": 0 }
```

`buttons.attract_program` is a list of pattern entries. Supported pattern names
in the current daemon are:

- `linear`
- `radial`
- `circular`
- `sequential_colors`

Pattern parameters are passed to the matching daemon pattern generator.
