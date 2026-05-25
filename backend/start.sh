#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Installing Kite Passport..."

curl -fsSL https://agentpassport.ai/install.sh | bash

export PATH="$HOME/.kpass/bin:$HOME/.local/bin:$PATH"
if [ -z "$KITE_PASSPORT_CLI_PATH" ] && [ -x "$HOME/.kpass/bin/kpass" ]; then
  export KITE_PASSPORT_CLI_PATH="$HOME/.kpass/bin/kpass"
fi

echo "Checking Kite Passport CLI..."
if command -v kpass >/dev/null 2>&1; then
  kpass version || true
elif command -v kite-passport >/dev/null 2>&1; then
  kite-passport version || true
else
  echo "WARNING: kpass CLI not found after install"
fi

echo "Checking config..."
echo "DEBUG: KITE_PASSPORT_CONFIG_JSON length = ${#KITE_PASSPORT_CONFIG_JSON}"
ls -la "$HOME/.kite-passport" || true
ls -la "$PWD/.kite-passport" || true

# If Passport config is provided via env var, create it
if [ -n "$KITE_PASSPORT_CONFIG_JSON" ]; then
  echo "Creating Passport config from KITE_PASSPORT_CONFIG_JSON env var"
  mkdir -p "$PWD/.kite-passport"
  echo "$KITE_PASSPORT_CONFIG_JSON" > "$PWD/.kite-passport/config.json"
  echo "✓ Passport config created from env var"
  ls -la "$PWD/.kite-passport/config.json" || true
else
  echo "DEBUG: KITE_PASSPORT_CONFIG_JSON env var is empty or not set"
fi

# If Passport config exists in the container home directory, mirror it into the backend folder.
if [ -f "$HOME/.kite-passport/config.json" ] && [ ! -f "$PWD/.kite-passport/config.json" ]; then
  echo "Copying Passport config from $HOME/.kite-passport to $PWD/.kite-passport"
  mkdir -p "$PWD/.kite-passport"
  cp -r "$HOME/.kite-passport/." "$PWD/.kite-passport/"
fi

if [ -f "$PWD/.kite-passport/config.json" ]; then
  export KITE_PASSPORT_CONFIG_PATH="$PWD/.kite-passport/config.json"
  echo "Exported KITE_PASSPORT_CONFIG_PATH=$KITE_PASSPORT_CONFIG_PATH"
fi

if [ ! -f "$HOME/.kite-passport/config.json" ] && [ ! -f "$PWD/.kite-passport/config.json" ]; then
  echo "WARNING: Passport config missing. Mount ~/.kite-passport or set KITE_PASSPORT_CONFIG_PATH to a valid config.json."
fi

echo "Starting backend..."

PORT=${PORT:-8080}
uvicorn main:app --host 0.0.0.0 --port $PORT