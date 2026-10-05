# Automatic Bell - Microcontroller

MicroPython firmware for ESP32-based automatic bell controller.

## Overview

This is the microcontroller firmware for the Automatic Bell system. It runs on an ESP32 and handles Wi-Fi connectivity, NTP time synchronization, schedule management, and relay control for the bell hardware.

## Features

- **Wi-Fi connectivity** with automatic reconnection
- **NTP time synchronization** for accurate scheduling
- **Schedule-based bell control** — configurable time slots
- **Web server** for configuration and manual override
- **RTC support** via DS1302 module
- **Error handling** and logging

## Tech Stack

- **Language:** MicroPython
- **Hardware:** ESP32, DS1302 RTC, relay module
- **Libraries:** `machine`, `network`, `ntptime`

## Flash to ESP32

```bash
esptool.py --port /dev/ttyUSB0 erase_flash
esptool.py --port /dev/ttyUSB0 write_flash -z 0x1000 micropython.bin
ampy --port /dev/ttyUSB0 put main.py
ampy --port /dev/ttyUSB0 put lib/
```

## Project Structure

```
├── main.py              # Entry point — Wi-Fi, NTP, schedule loop
└── lib/
    ├── wlan.py          # Wi-Fi connection management
    ├── clock.py         # NTP sync and timekeeping
    ├── schedule.py      # Bell schedule logic
    ├── webserver.py     # Configuration web server
    ├── ds1302.py        # RTC module driver
    ├── switch.py        # Relay/switch control
    ├── config.py        # Configuration constants
    ├── utils.py         # Utility functions
    ├── error.py         # Error handling
    └── log.py           # Logging
```

## License

MIT
