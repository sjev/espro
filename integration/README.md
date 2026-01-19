# Home Assistant + MQTT Integration Stack

Disposable Home Assistant environment for testing espro MQTT integration.

## Quick Start

```bash
cd integration
docker compose up -d
```

Access Home Assistant at http://localhost:8123 .

Credentials:

* user: admin
* pass: admin123

## Services

| Service | Port | Description |
|---------|------|-------------|
| Home Assistant | 8123 | Web UI |
| MQTT | 1883 | Broker (TCP) |
| MQTT WebSocket | 9001 | Broker (WS) |

## Reset

```bash
docker compose down
docker volume rm integration_ha-data
docker compose up -d
```

No manual setup needed - snapshot auto-restores with MQTT configured.

## Architecture

```
integration/
├── docker-compose.yml       # Service orchestration
├── create-snapshot.sh       # Developer tool: create new snapshot
├── test_autodiscovery.sh    # Test MQTT autodiscovery
└── ha/                      # Container files (mounted into HA)
    ├── configuration.yaml   # Base HA config
    ├── init-ha.sh           # Container entrypoint
    └── snapshot/            # Golden .storage state
```

**Snapshot lifecycle:**
- `create-snapshot.sh` runs on your host to create a new snapshot (one-time setup)
- `ha/init-ha.sh` runs inside the container on every start, restoring the snapshot if `.storage` is missing

## Creating a New Snapshot

If you need to update the snapshot (e.g., change credentials, add integrations):

```bash
./create-snapshot.sh
```

The script will guide you through the process.

## MQTT Autodiscovery

Devices publish config to `homeassistant/<component>/<node_id>/<object_id>/config`.

Example sensor:

```bash
mosquitto_pub -h localhost -t "homeassistant/sensor/mydevice/temperature/config" -m '{
  "name": "Temperature",
  "unique_id": "mydevice_temperature",
  "state_topic": "espro/mydevice/temperature",
  "unit_of_measurement": "°C",
  "device": {
    "identifiers": ["mydevice"],
    "name": "My Device",
    "manufacturer": "espro"
  }
}'
```

Then publish state:

```bash
mosquitto_pub -h localhost -t "espro/mydevice/temperature" -m "23.5"
```

## Testing

```bash
./test_autodiscovery.sh
```

Or manually:

```bash
docker exec mosquitto mosquitto_sub -t "#" -v
docker exec mosquitto mosquitto_pub -t "test/topic" -m "hello"
```
