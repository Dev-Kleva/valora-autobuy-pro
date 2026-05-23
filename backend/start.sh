#!/bin/bash

set -e

echo "Installing Kite Passport..."

curl -fsSL https://agentpassport.ai/install.sh | bash

export PATH="$HOME/.local/bin:$PATH"

echo "Initializing Kite Passport..."

if command -v kpass >/dev/null 2>&1; then
  kpass init || true
elif command -v kite-passport >/dev/null 2>&1; then
  kite-passport init || true
else
  echo "WARNING: kpass CLI not found after install"
fi

echo "Checking config..."
ls -la ~/.kite-passport || true
ls -la /app/.kite-passport || true

# If Passport config exists in the container home directory, mirror it into /app for the backend.
if [ -f "$HOME/.kite-passport/config.json" ] && [ ! -f "/app/.kite-passport/config.json" ]; then
  echo "Copying Passport config from $HOME/.kite-passport to /app/.kite-passport"
  mkdir -p /app/.kite-passport
  cp -r "$HOME/.kite-passport/." /app/.kite-passport/
fi

if [ ! -f "$HOME/.kite-passport/config.json" ] && [ ! -f "/app/.kite-passport/config.json" ]; then
  echo "WARNING: Passport config missing. Mount ~/.kite-passport or set KITE_PASSPORT_CONFIG_PATH to a valid config.json."
fi

echo "Starting backend..."

PORT=${PORT:-8080}
uvicorn main:app --host 0.0.0.0 --port $PORT