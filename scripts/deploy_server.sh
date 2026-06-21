#!/bin/bash
# Deploy or update the server + dashboard via Docker Compose
# Usage: bash deploy_server.sh [--update]

set -e

COMPOSE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../docker" && pwd)"
cd "$COMPOSE_DIR"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env — please fill in your ANTHROPIC_API_KEY and JWT_SECRET, then re-run."
  exit 1
fi

if [ "$1" = "--update" ]; then
  docker compose pull
  docker compose up -d --build
  echo "Updated!"
else
  docker compose up -d --build
  echo "Deployed! Dashboard at http://localhost:3000"
  echo "API at http://localhost:8000"
  echo "Default admin: snehapathak752@gmail.com / changeme123"
  echo "Change your password in Settings after first login."
fi
