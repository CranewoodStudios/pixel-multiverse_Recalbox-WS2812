# Pixel Multiverse - Recalbox WS2812 Integration

![Project Status](https://img.shields.io/badge/status-active-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)
![Platform](https://img.shields.io/badge/platform-Recalbox-red)

## Overview

**Pixel Multiverse** is a sophisticated lighting control system designed specifically for Recalbox emulation platforms. This project integrates WS2812 (NeoPixel) addressable LED strips with Recalbox, enabling dynamic, game-aware lighting effects that synchronize with your gaming experience.

The system allows you to control RGB LED animations and effects based on:
- Active game and emulator selection
- Game state changes
- Custom themes and color schemes
- Real-time system events

## Features

### Core Capabilities
- **WS2812 LED Strip Support**: Full control of addressable RGB LED strips
- **Game-Aware Lighting**: Automatic lighting adjustments based on the active game/emulator
- **Dynamic Effects**: Multiple animation patterns and color transitions
- **Customizable Themes**: Create and manage custom lighting themes per game
- **System Integration**: Seamless integration with Recalbox ecosystem
- **Performance Optimized**: Lightweight design suitable for low-power Raspberry Pi devices

### Lighting Effects
- Solid colors
- Breathing/pulse effects
- Rainbow cycles
- Color gradients
- Smooth transitions
- Custom animation sequences

## Hardware Requirements

- **LED Controller Board**: WS2812 compatible controller (GPIO-based)
- **LED Strip**: WS2812B or equivalent addressable RGB LED strip
- **Recalbox Device**: Raspberry Pi 3, 4, or equivalent
- **Power Supply**: Adequate power supply for LED strip (typically 5V)
- **GPIO Pins**: Available GPIO pins on Recalbox device

## Software Requirements

- **Recalbox**: Version 7.0 or higher
- **Python**: 3.6+
- **Dependencies**: Listed in `requirements.txt`

## Installation

### 1. Clone the Repository

```bash
cd /home/pi
git clone https://github.com/CranewoodStudios/pixel-multiverse_Recalbox-WS2812.git
cd pixel-multiverse_Recalbox-WS2812
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Hardware Setup

1. Connect your WS2812 LED strip to the GPIO pins on your Recalbox device
2. Configure the GPIO pin number in the configuration file
3. Ensure proper power supply for the LED strip
4. Test the connection before full installation

### 4. Configuration

Edit `config.json` to set your preferences:

```json
{
  "gpio_pin": 18,
  "led_count": 30,
  "brightness": 255,
  "default_theme": "default"
}
```

### 5. Enable Auto-Start

Add the service to Recalbox's autostart:

```bash
sudo systemctl enable pixel-multiverse
sudo systemctl start pixel-multiverse
```

## Configuration

### Main Configuration File (`config.json`)

```json
{
  "gpio_pin": 18,
  "led_count": 30,
  "brightness": 255,
  "animation_speed": 100,
  "default_theme": "default",
  "emulator_themes": {
    "snes": "snes-theme",
    "nes": "nes-theme",
    "genesis": "genesis-theme"
  }
}
```

### Theme Configuration

Create custom themes in the `themes/` directory:

```json
{
  "name": "snes-theme",
  "colors": {
    "primary": [128, 0, 128],
    "secondary": [255, 165, 0],
    "accent": [0, 255, 0]
  },
  "animation": "pulse",
  "speed": 100
}
```

## Usage

### Basic Operation

Once installed and configured, the system operates automatically:

1. Launch Recalbox
2. Select a game
3. The LED strip will automatically change to the theme associated with that game's emulator
4. Animations will continue during gameplay and menus

### Manual Control

You can control the lighting manually using the API:

```python
from pixel_multiverse import LEDController

controller = LEDController(gpio_pin=18, led_count=30)
controller.set_color([255, 0, 0])  # Red
controller.pulse([0, 255, 0])      # Green pulse
controller.rainbow()               # Rainbow animation
```

### Available Commands

- `set_color(rgb)` - Set solid color
- `pulse(rgb, speed)` - Pulse animation
- `fade(rgb1, rgb2, speed)` - Fade between colors
- `rainbow(speed)` - Rainbow cycle animation
- `off()` - Turn off LEDs

## API Reference

### LEDController Class

**Initialize:**
```python
controller = LEDController(gpio_pin=18, led_count=30, brightness=255)
```

**Methods:**
- `set_color(r, g, b)` - Set all LEDs to a specific color
- `set_pixel(index, r, g, b)` - Set individual LED
- `pulse(r, g, b, speed=50)` - Create pulse effect
- `fade(r1, g1, b1, r2, g2, b2, speed=50)` - Fade between two colors
- `rainbow(speed=50)` - Display rainbow animation
- `clear()` - Turn off all LEDs
- `show()` - Apply changes to LED strip
- `brightness(level)` - Adjust brightness (0-255)

## Troubleshooting

### LEDs Not Responding

1. Verify GPIO pin configuration
2. Check power supply to LED strip
3. Ensure proper wiring connections
4. Check for permission issues: `sudo usermod -aG gpio pi`

### Performance Issues

1. Reduce LED count in configuration
2. Lower animation speed
3. Reduce brightness
4. Check CPU usage: `top`

### Configuration Not Loading

1. Verify JSON syntax in config file
2. Check file permissions: `chmod 644 config.json`
3. Review logs: `journalctl -u pixel-multiverse -f`

## Project Structure

```
pixel-multiverse_Recalbox-WS2812/
├── README.md
├── requirements.txt
├── setup.py
├── config.json
├── src/
│   ├── __init__.py
│   ├── led_controller.py
│   ├── theme_manager.py
│   ├── emulator_detector.py
│   └── animation_engine.py
├── themes/
│   ├── default.json
│   ├── snes-theme.json
│   ├── nes-theme.json
│   └── genesis-theme.json
├── tests/
│   ├── test_led_controller.py
│   └── test_theme_manager.py
└── docs/
    ├── INSTALLATION.md
    ├── CONFIGURATION.md
    └── API.md
```

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -am 'Add new feature'`
4. Push to branch: `git push origin feature/my-feature`
5. Submit a pull request

### Code Style

- Follow PEP 8 guidelines
- Use 4-space indentation
- Include docstrings for all functions
- Write unit tests for new features

## Performance Considerations

- LED update frequency is optimized for 60Hz refresh rate
- Animations run in separate threads to prevent blocking
- Memory footprint is minimal (~50MB base)
- CPU usage scales with LED count and animation complexity

## Security

- GPIO access is restricted to authorized users
- Configuration files should have restrictive permissions
- No external network connectivity required for core functionality
- Regular security updates recommended

## Future Enhancements

- [ ] Web-based configuration dashboard
- [ ] Mobile app control interface
- [ ] Advanced pattern designer
- [ ] Music visualization integration
- [ ] Multi-zone LED support
- [ ] Wireless control options

## Known Issues

- Initial boot may take 2-3 seconds for LED initialization
- Very high LED counts (500+) may require optimization
- Some animation effects use more CPU on older Raspberry Pi models

## Support and Documentation

- **Issues**: [GitHub Issues](https://github.com/CranewoodStudios/pixel-multiverse_Recalbox-WS2812/issues)
- **Discussions**: [GitHub Discussions](https://github.com/CranewoodStudios/pixel-multiverse_Recalbox-WS2812/discussions)
- **Documentation**: See `/docs` folder for detailed guides

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Changelog

### Version 1.0.0 (2026-01-06)
- Initial release
- Core WS2812 LED control
- Recalbox integration
- Theme system
- Basic animations

## Authors

- **CranewoodStudios** - Project Creator and Maintainer

## Acknowledgments

- Recalbox community for platform support
- WS2812 library contributors
- All beta testers and contributors

## Contact

For questions, suggestions, or feedback:
- GitHub: [@CranewoodStudios](https://github.com/CranewoodStudios)
- Issues: [Create an Issue](https://github.com/CranewoodStudios/pixel-multiverse_Recalbox-WS2812/issues)

---

**Last Updated**: 2026-01-06
**Status**: Actively Maintained ✓
