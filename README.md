# Home Assistant LoJack Integration

A Home Assistant integration for [Spireon LoJack](https://www.spireon.com/lojack/) vehicle tracking. Track your vehicles on the Home Assistant map with real-time GPS location, speed, heading, and vehicle telemetry.

## Features

- **Vehicle Tracking**: Real-time GPS location displayed on the Home Assistant map
- **Vehicle Telemetry**: Dedicated sensor entities for speed, odometer, and battery voltage
- **Vehicle Status**: Binary sensors for connectivity and movement status
- **Vehicle Information**: Diagnostic sensors for VIN, make, model, year, and license plate
- **Multi-Vehicle Support**: Track all vehicles associated with your LoJack account
- **Automatic Token Refresh**: Seamless re-authentication when tokens expire

## Requirements

- Home Assistant 2024.1.0 or newer
- Active Spireon LoJack account with at least one tracked vehicle
- LoJack account credentials (username and password)

## Installation

### HACS Installation (Recommended)

1. Open HACS in your Home Assistant instance
2. Click the three dots in the top right corner and select **Custom repositories**
3. Add `https://github.com/devinslick/homeassistant_lojack` as a custom repository with category **Integration**
4. Search for "LoJack" in HACS and click **Download**
5. Restart Home Assistant

### Manual Installation

1. Download the `custom_components/lojack` directory from this repository
2. Copy it to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

1. Navigate to **Settings** → **Devices & Services** → **Add Integration**
2. Search for and select **LoJack**
3. Enter your LoJack account credentials:
   - **Username**: Your Spireon LoJack account email
   - **Password**: Your Spireon LoJack account password
4. Click **Submit**

The integration will automatically discover all vehicles associated with your account and create device tracker entities for each one.

## Entities

The integration creates multiple entities for each vehicle:

### Device Tracker

Each vehicle creates a device tracker entity that shows the vehicle's location on the map:

| Attribute | Description |
|-----------|-------------|
| `latitude` | Current GPS latitude |
| `longitude` | Current GPS longitude |
| `gps_accuracy` | Location accuracy in meters |
| `address` | Formatted address of current location |
| `heading` | Direction of travel (degrees) |

### Sensors

Regular sensors provide real-time vehicle telemetry:

| Entity | Description | Unit |
|--------|-------------|------|
| `sensor.{name}_odometer` | Total mileage | miles |
| `sensor.{name}_speed` | Current speed | mph |
| `sensor.{name}_battery_voltage` | Vehicle battery voltage | V |
| `sensor.{name}_location_last_reported` | Timestamp of last location update | timestamp |

### Binary Sensors

Binary sensors provide status information:

| Entity | Description |
|--------|-------------|
| `binary_sensor.{name}_active` | Connectivity status |
| `binary_sensor.{name}_moving` | Whether vehicle is currently moving |

### Diagnostic Sensors

Diagnostic sensors (disabled by default) provide vehicle information:

| Entity | Description |
|--------|-------------|
| `sensor.{name}_make` | Vehicle manufacturer |
| `sensor.{name}_model` | Vehicle model |
| `sensor.{name}_year` | Vehicle year |
| `sensor.{name}_vin` | Vehicle Identification Number |
| `sensor.{name}_license_plate` | License plate number |

*Note: `{name}` is the vehicle name, typically in the format "Year Make Model" (e.g., "2024_ford_f150")*

## Example Automations

### Notify When Vehicle Leaves Home

```yaml
automation:
  - alias: "Vehicle Left Home"
    trigger:
      - platform: state
        entity_id: device_tracker.2024_ford_f150
        from: "home"
    action:
      - service: notify.mobile_app
        data:
          title: "Vehicle Alert"
          message: "Your F-150 has left home"
```

### Track Low Battery Voltage

```yaml
automation:
  - alias: "Low Vehicle Battery Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.2024_ford_f150_battery_voltage
        below: 12.0
    action:
      - service: notify.mobile_app
        data:
          title: "Battery Alert"
          message: "Your vehicle battery is low: {{ states('sensor.2024_ford_f150_battery_voltage') }}V"
```

### Notify When Vehicle Starts Moving

```yaml
automation:
  - alias: "Vehicle Started Moving"
    trigger:
      - platform: state
        entity_id: binary_sensor.2024_ford_f150_moving
        from: "off"
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Vehicle Alert"
          message: "Your F-150 has started moving"
```

## Polling Interval

The integration polls the LoJack API every 5 minutes by default. This balances timely updates with API rate limits.

## Troubleshooting

### Authentication Failed

- Verify your username and password are correct
- Ensure your LoJack account is active and in good standing
- Check that you can log in to the LoJack mobile app

### No Vehicles Found

- Confirm you have at least one vehicle registered in your LoJack account
- Verify the vehicle's tracking device is active and reporting

### Location Not Updating

- Check that the vehicle's LoJack device has cellular connectivity
- The vehicle may need to be started or moved for a fresh GPS fix

## Privacy & Security

- Credentials are stored securely in Home Assistant's encrypted storage
- All API communication uses HTTPS
- Tokens are automatically refreshed to maintain security

## Disclaimer

This integration is not affiliated with, endorsed by, or connected to Spireon or LoJack. The names Spireon and LoJack are trademarks or registered trademarks of Spireon and its subsidiaries. This project was developed using the publicly available [lojack-clients](https://pypi.org/project/lojack-clients/) Python package.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

If you encounter issues or have feature requests, please [open an issue](https://github.com/devinslick/homeassistant_lojack/issues) on GitHub.
