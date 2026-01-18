#!/bin/bash
# Restore snapshot if .storage doesn't exist
if [ ! -d /config/.storage ]; then
  echo "Restoring snapshot..."
  cp -r /snapshot/.storage /config/
fi
exec /init
