#!/bin/bash

echo "Installing Kite Passport..."

curl -fsSL https://agentpassport.ai/install.sh | bash

export PATH="$HOME/.local/bin:$PATH"

echo "Starting FastAPI server..."

PORT=${PORT:-8000}

uvicorn main:app --host 0.0.0.0 --port $PORT