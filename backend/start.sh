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

echo "Starting backend..."

PORT=${PORT:-8080}
uvicorn main:app --host 0.0.0.0 --port $PORT