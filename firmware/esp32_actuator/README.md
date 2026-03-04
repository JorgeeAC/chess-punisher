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

- Update `platformio.ini` `build_flags` with your Wi-Fi and broker settings.
- This skeleton subscribes to `cp/actuators/<device_id>/cmd` and publishes ACK/status topics.
- Servo control is intentionally left as a TODO in `src/main.cpp`.
