# Home Assistant LoJack Integration

A Home Assistant integration for [Spireon LoJack](https://www.spireon.com/lojack/) vehicle tracking. Track your vehicles on the Home Assistant map with real-time GPS location, speed, heading, and vehicle telemetry.

## Features

- **Vehicle Tracking**: Real-time GPS location displayed on the Home Assistant map
- **Vehicle Telemetry**: Speed, heading, odometer, and battery voltage
- **Vehicle Information**: VIN, make, model, year, color, and license plate
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

### Device Tracker

Each vehicle creates a device tracker entity with the following attributes:

| Attribute | Description |
|-----------|-------------|
| `latitude` | Current GPS latitude |
| `longitude` | Current GPS longitude |
| `gps_accuracy` | Location accuracy in meters |
| `vin` | Vehicle Identification Number |
| `make` | Vehicle manufacturer |
| `model` | Vehicle model |
| `year` | Vehicle year |
| `color` | Vehicle color |
| `license_plate` | License plate number |
| `speed` | Current speed (mph) |
| `heading` | Direction of travel (degrees) |
| `odometer` | Total mileage (miles) |
| `battery_voltage` | Vehicle battery voltage |
| `address` | Formatted address of current location |
| `gps_quality` | GPS fix quality indicator |
| `last_updated` | Timestamp of last location update |

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
      - platform: template
        value_template: >
          {{ state_attr('device_tracker.2024_ford_f150', 'battery_voltage') | float < 12.0 }}
    action:
      - service: notify.mobile_app
        data:
          title: "Battery Alert"
          message: "Your vehicle battery is low: {{ state_attr('device_tracker.2024_ford_f150', 'battery_voltage') }}V"
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
