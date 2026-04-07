# ESP32 Actuator Firmware

PlatformIO project for a single actuator node.

## Build

```bash
cd firmware/esp32_actuator
pio run -e esp32dev
```

## Flash

```bash
cd firmware/esp32_actuator
pio run -e esp32dev -t upload --upload-port /dev/ttyUSB0
```

## Notes

- Update `platformio.ini` `build_flags` with your Wi-Fi settings.
- The firmware exposes `GET /health` and `GET /punish` on port 80.
- `GET /punish` accepts query params like `severity`, `loss`, `move`, and optional `pulse_ms`.
- The default bring-up behavior is a brief LED pulse plus serial logging in `src/main.cpp`.
