#!/usr/bin/env bash
# Run elaas-backend as a container on an AWS EC2 (or any Linux) VM.
# Usage: ./scripts/run-on-aws-vm.sh [--build|--pull|--compose]
#   --build   (default) Build image and run with docker run
#   --pull    Use IMAGE=... (e.g. ECR URI), pull and run
#   --compose Use docker compose up -d
set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-elaas-backend}"
IMAGE_NAME="${IMAGE_NAME:-elaas-backend:latest}"
PORT="${PORT:-8080}"
ENV_FILE="${ENV_FILE:-.env}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
  echo "Usage: $0 [OPTIONS]"
  echo "  --build   Build image and run (default)"
  echo "  --pull   Pull IMAGE and run (set IMAGE=... e.g. ECR URI)"
  echo "  --compose Run via docker compose up -d"
  echo "Env: CONTAINER_NAME, IMAGE_NAME, IMAGE, PORT, ENV_FILE"
  exit 0
}

MODE=build
for arg in "${@:-}"; do
  case "$arg" in
    --pull)   MODE=pull ;;
    --compose) MODE=compose ;;
    --build)  MODE=build ;;
    -h|--help) usage ;;
  esac
done

cd "$ROOT_DIR"

if ! command -v docker &>/dev/null; then
  echo "Error: Docker is not installed or not in PATH. Install Docker and retry."
  exit 1
fi

ENV_FILE_ARG=()
if [[ -f "$ENV_FILE" ]]; then
  ENV_FILE_ARG=(--env-file "$ENV_FILE")
else
  echo "Warning: $ENV_FILE not found. Copy .env.example to .env and configure it."
  if [[ -t 0 ]] && [[ "${SKIP_ENV_CHECK:-}" != "1" ]]; then
    read -r -p "Continue anyway? [y/N] " c
    if [[ "${c,,}" != "y" ]]; then
      exit 1
    fi
  else
    echo "Set SKIP_ENV_CHECK=1 to run without .env (e.g. CI). Exiting."
    exit 1
  fi
fi

run_with_docker_run() {
  local image="$1"
  docker stop "$CONTAINER_NAME" 2>/dev/null || true
  docker rm "$CONTAINER_NAME" 2>/dev/null || true
  docker run -d \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    -p "${PORT}:8080" \
    "${ENV_FILE_ARG[@]}" \
    "$image"
}

case "$MODE" in
  build)
    docker build -t "$IMAGE_NAME" .
    run_with_docker_run "$IMAGE_NAME"
    ;;
  pull)
    if [[ -z "${IMAGE:-}" ]]; then
      echo "Error: For --pull set IMAGE= (e.g. 123456789.dkr.ecr.us-east-1.amazonaws.com/elaas-backend:latest)"
      exit 1
    fi
    docker pull "$IMAGE"
    run_with_docker_run "$IMAGE"
    ;;
  compose)
    if ! command -v docker &>/dev/null; then
      echo "Error: docker compose not available. Use Docker Compose V2 or install compose plugin."
      exit 1
    fi
    export PORT
    docker compose up -d --build
    echo "Started with docker compose. Check: docker compose ps"
    exit 0
    ;;
esac

echo "Container started: $CONTAINER_NAME"
echo "  Port: $PORT"
echo "  Logs: docker logs -f $CONTAINER_NAME"
echo "  Health: curl http://localhost:$PORT/health"
