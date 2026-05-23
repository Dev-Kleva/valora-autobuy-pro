#!/bin/bash

set -e

echo "Installing Kite Passport..."

curl -fsSL https://agentpassport.ai/install.sh | bash

export PATH="$HOME/.local/bin:$PATH"

echo "Initializing Kite Passport..."

# THIS is the missing step (critical)
kite-passport init || true

echo "Checking config..."
ls -la ~/.kite-passport || true
ls -la /app/.kite-passport || true

echo "Starting backend..."

PORT=${PORT:-8080}
uvicorn main:app --host 0.0.0.0 --port $PORT