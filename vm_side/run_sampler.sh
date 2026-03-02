#!/bin/bash

set -e

echo "Starting embedded_device..."
(
  cd embedded_device
  make run
) &
EMBED_PID=$!

sleep 3

echo "Running samples_reader..."
(
  cd samples_reader
  make run
)

echo "Stopping embedded_device..."
kill "$EMBED_PID" 2>/dev/null || true
