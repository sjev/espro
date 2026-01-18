# Home Assistant + MQTT Integration Stack

Disposable Home Assistant environment for testing espro MQTT integration.

## Quick Start

```bash
cd integration
docker compose up -d
```

1. Access Home Assistant at http://localhost:8123
2. Complete onboarding (create account)
3. Add MQTT integration: **Settings > Devices & Services > Add Integration > MQTT**
   - Broker: `mosquitto`
   - Port: `1883`

## Services

| Service | Port | Description |
|---------|------|-------------|
| Home Assistant | 8123 | Web UI |
| MQTT | 1883 | Broker (TCP) |
| MQTT WebSocket | 9001 | Broker (WS) |

## Home Assistant

* [localhost:8123](http://localhost:8123)
* user: admin
* pass: admin123


## Reset Home Assistant

Delete HA state while preserving MQTT broker data:

```bash
docker compose down
rm -rf ha-data
docker compose up -d
```

After reset, complete HA onboarding and re-add MQTT integration.

## Full Reset (including MQTT)

```bash
docker compose down -v
rm -rf ha-data
docker compose up -d
```

## Architecture

- `configuration.yaml` - Mounted read-only, persists across resets
- `ha-data/` - HA state directory, delete to reset
- `mosquitto-data` - Named volume for MQTT persistence

## MQTT Testing

Publish a test message:

```bash
docker exec mosquitto mosquitto_pub -t "test/topic" -m "hello"
```

Subscribe to all topics:

```bash
docker exec mosquitto mosquitto_sub -t "#" -v
```
