#!/bin/bash
# Test MQTT autodiscovery by publishing a fake sensor

set -e

BROKER="${MQTT_BROKER:-localhost}"
TOPIC_CONFIG="homeassistant/sensor/test_device/temperature/config"
TOPIC_STATE="espro/test_device/temperature"

echo "Publishing autodiscovery config to $TOPIC_CONFIG..."
mosquitto_pub -h "$BROKER" -t "$TOPIC_CONFIG" -m '{
  "name": "Test Temperature",
  "unique_id": "test_device_temperature",
  "state_topic": "espro/test_device/temperature",
  "unit_of_measurement": "°C",
  "device": {
    "identifiers": ["test_device"],
    "name": "Test Device",
    "manufacturer": "espro"
  }
}'

echo "Publishing state value to $TOPIC_STATE..."
mosquitto_pub -h "$BROKER" -t "$TOPIC_STATE" -m "23.5"

echo "Done. Check HA: Settings > Devices & Services > MQTT"
