#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "=== Home Assistant Snapshot Creator ==="
echo ""

# Check if snapshot already exists
if [ -d "ha/snapshot" ]; then
  read -p "Snapshot already exists. Delete and create new? [y/N] " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
  fi
  rm -rf ha/snapshot
fi

# Stop any running containers
echo "Stopping containers..."
docker compose down 2>/dev/null || true

# Remove existing volume
echo "Removing existing HA volume..."
docker volume rm integration_ha-data 2>/dev/null || true

# Start without snapshot (will use default HA setup)
echo "Starting fresh HA instance..."
echo "(This may take a moment on first run)"
docker compose up -d

echo ""
echo "=== Manual Setup Required ==="
echo ""
echo "1. Open http://localhost:8123"
echo "2. Complete onboarding (create account)"
echo "3. Add MQTT integration:"
echo "   - Settings > Devices & Services > Add Integration > MQTT"
echo "   - Broker: mosquitto"
echo "   - Port: 1883"
echo ""
read -p "Press Enter when setup is complete..."

# Stop HA
echo ""
echo "Stopping HA to export snapshot..."
docker compose down

# Export snapshot
echo "Exporting snapshot..."
docker run --rm \
  -v integration_ha-data:/data:ro \
  -v "$(pwd)":/backup \
  alpine cp -r /data/.storage /backup/ha/snapshot

echo ""
echo "=== Snapshot Created ==="
echo ""
echo "Snapshot saved to: $(pwd)/ha/snapshot"
echo ""
echo "Starting HA with snapshot..."
docker compose up -d

echo ""
echo "Done! HA is running with the new snapshot."
echo "Future resets will auto-restore this snapshot."
