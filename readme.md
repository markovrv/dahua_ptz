# Dahua PTZ Camera Integration for Home Assistant

![Home Assistant](https://img.shields.io/badge/Home_Assistant-2023.12-blue?logo=home-assistant&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python&logoColor=white)
![License](https://img.shields.io/github/license/markovrv/dahua-ptz-ha)

A custom Home Assistant integration for controlling Dahua PTZ cameras via RPC protocol with advanced features and automation support.

## Features

- 🎥 Full PTZ control (pan/tilt/zoom)
- 🔄 Automatic reconnection handling
- ⚡ Asynchronous API calls
- 🔧 Configurable via UI or YAML
- 🔄 Integration restart without HA reboot
- 🛠️ Multiple camera support
- 📊 Detailed logging

## Installation

### Method 1: HACS (Recommended)
1. Go to HACS → Integrations
2. Click "+ Explore & Download Repositories"
3. Search for "Dahua PTZ"
4. Install the repository
5. Restart Home Assistant

### Method 2: Manual Installation
1. Clone this repository or download the latest release
2. Copy the `dahua_ptz` folder to your `custom_components` directory
3. Restart Home Assistant

```bash
cd /config/custom_components
git clone https://github.com/markovrv/dahua-ptz-ha.git dahua_ptz
```

## Configuration

### UI Configuration (Recommended)
1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Dahua PTZ"
4. Enter your camera details:
   - Host/IP address
   - Username
   - Password
   - Force text mode (if experiencing JSON parsing issues)

### YAML Configuration
```yaml
dahua_ptz:
  host: 192.168.1.100
  username: admin
  password: your_password
  force_text: false  # Set to true if having JSON parsing issues
```

## Services

### ptz_control
Control PTZ movements:
```yaml
service: dahua_ptz.ptz_control
data:
  action: start  # or "stop"
  code: PositionABS  # or "Left", "Right", "Up", "Down"
  arg1: 1800  # Horizontal position (in 0.1° units)
  arg2: 100   # Vertical position (in 0.1° units)
  arg3: 5     # Speed (1-10)
```

### restart
Restart the integration without HA reboot:
```yaml
service: dahua_ptz.restart
```

## Example Automations

### Preset Positions Switch
```yaml
switch:
  - platform: template
    switches:
      ptz_preset_1:
        friendly_name: "PTZ Preset 1"
        turn_on:
          - service: dahua_ptz.ptz_control
            data:
              action: start
              code: PositionABS
              arg1: 1800
              arg2: 100
              arg3: 5
```

### Motion Tracking
```yaml
automation:
  - alias: "PTZ Follow Motion"
    trigger:
      platform: state
      entity_id: binary_sensor.motion_detector
      to: "on"
    action:
      service: dahua_ptz.ptz_control
      data:
        action: start
        code: PositionABS
        arg1: "{{ states('input_number.motion_x_position') | float * 10 }}"
        arg2: "{{ states('input_number.motion_y_position') | float * 10 }}"
```

## Troubleshooting

### Common Issues
1. **Connection errors**: Verify camera credentials and network connectivity
2. **JSON parsing errors**: Set `force_text: true` in configuration
3. **Slow response**: Reduce PTZ movement speed (arg3)

Enable debug logging for detailed troubleshooting:
```yaml
logger:
  default: info
  logs:
    custom_components.dahua_ptz: debug
```

## Contributing

Pull requests are welcome! Please follow these guidelines:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and feature requests, please [open an issue](https://github.com/markovrv/dahua-ptz-ha/issues).

---

**Disclaimer**: This is an unofficial integration not affiliated with Dahua Technology.
