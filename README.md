# Kärcher Home Robots — Home Assistant Integration

Integrate your **Kärcher RCV5** (and RCV3 / RCF3) robot vacuum into Home Assistant via the Kärcher Home Robots cloud API.

## Features

- **Vacuum entity** — start, stop, pause, and return to dock from HA or automations
- **Battery sensor** — track charge level
- Polls every 30 seconds for live state updates
- Config UI — set up via Settings → Integrations (no YAML needed)

## Installation via HACS

1. In HACS, go to **Integrations → Custom repositories**
2. Add this repository URL and set the category to **Integration**
3. Search for **Kärcher Home Robots** and install
4. Restart Home Assistant
5. Go to **Settings → Devices & Services → Add Integration** and search for **Kärcher**
6. Enter your Kärcher Home Robots app email and password

## Manual Installation

1. Copy the `custom_components/karcher_home_robots` folder into your HA `config/custom_components/` directory
2. Restart Home Assistant
3. Add the integration via **Settings → Devices & Services**

## Requirements

- A Kärcher Home Robots account (the same one you use in the mobile app)
- Your robot must already be set up and linked in the Kärcher Home Robots app

## Supported Models

- Kärcher RCV5
- Kärcher RCV3
- Kärcher RCF3

## Notes

This integration uses the same cloud API as the official Kärcher Home Robots app. It requires an internet connection and Kärcher's servers to be reachable. This is an unofficial community integration and is not affiliated with Kärcher.
