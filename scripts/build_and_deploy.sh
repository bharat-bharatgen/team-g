#!/usr/bin/env bash
# build_and_deploy.sh
#
# Usage (local):  ./scripts/build_and_deploy.sh [patch|minor|major]
# Usage (CI):     called by .github/workflows/deploy.yml on workflow_dispatch
#
# Steps:
#   1. Read current version from latest git tag, compute new version
#   2. Save previous images for rollback
#   3. Build Docker images with APP_VERSION baked in
#   4. Tag built images as <version>_<short-commit-hash>
#   5. Deploy with docker compose
#   6. Health check — verify backend is up
#   Rollback: if any step fails, restore previous images and restart

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/docker-compose.yml"

# --------------------------------------------------------------------------
# 1. Read current version from latest git tag, compute new version
# --------------------------------------------------------------------------
BUMP="${1:-patch}"   # patch | minor | major

# Get latest tag. Fall back to 0.0.0 if no tags exist.
current="$(git -C "$REPO_ROOT" describe --tags --abbrev=0 2>/dev/null || echo "0.0.0")"
IFS='.' read -r major minor patch <<< "$current"

# Validate that version components are integers
if ! [[ "$major" =~ ^[0-9]+$ ]] || ! [[ "$minor" =~ ^[0-9]+$ ]] || ! [[ "$patch" =~ ^[0-9]+$ ]]; then
  echo "ERROR: Latest git tag '$current' is not a valid version. Expected format: X.Y.Z"
  exit 1
fi

case "$BUMP" in
  major) major=$((major + 1)); minor=0; patch=0 ;;
  minor) minor=$((minor + 1)); patch=0 ;;
  patch) patch=$((patch + 1)) ;;
  *)
    echo "ERROR: unknown bump type '$BUMP'. Use patch, minor, or major."
    exit 1
    ;;
esac

new_version="$major.$minor.$patch"
echo "Will bump version: $current → $new_version"

# --------------------------------------------------------------------------
# 2. Save previous image IDs for rollback
# --------------------------------------------------------------------------
prev_backend="$(docker images insure-copilot-be:latest --format '{{.ID}}' 2>/dev/null || true)"
prev_frontend="$(docker images insure-copilot-fe:latest --format '{{.ID}}' 2>/dev/null || true)"
prev_worker="$(docker images insure-copilot-worker:latest --format '{{.ID}}' 2>/dev/null || true)"

rollback() {
  echo ""
  echo "ERROR: Deploy failed. Rolling back to previous images..."

  # Retag previous images back to latest if they existed
  if [ -n "$prev_backend" ];  then docker tag "$prev_backend"  insure-copilot-be:latest;     fi
  if [ -n "$prev_frontend" ]; then docker tag "$prev_frontend" insure-copilot-fe:latest;     fi
  if [ -n "$prev_worker" ];   then docker tag "$prev_worker"   insure-copilot-worker:latest; fi

  # Restart with previous images
  docker compose -f "$COMPOSE_FILE" up -d --no-build
  echo "Rollback complete. Running previous version: $current"
}

trap rollback ERR

# --------------------------------------------------------------------------
# 3. Build images with version baked in
# --------------------------------------------------------------------------
VITE_API_BASE_URL="${VITE_API_BASE_URL:-/api/v1}"
VITE_APP_NAME="${VITE_APP_NAME:-InsureCopilot}"

echo "Building images (version: $new_version, VITE_API_BASE_URL: $VITE_API_BASE_URL)..."

docker compose -f "$COMPOSE_FILE" build \
  --build-arg VITE_API_BASE_URL="$VITE_API_BASE_URL" \
  --build-arg VITE_APP_NAME="$VITE_APP_NAME" \
  --build-arg APP_VERSION="$new_version"

# --------------------------------------------------------------------------
# 4. Tag built images with versioned snapshot tag
# --------------------------------------------------------------------------
short_hash="$(git -C "$REPO_ROOT" rev-parse --short HEAD)"
TAG="${new_version}_${short_hash}"

docker tag insure-copilot-be:latest     "insure-copilot-be:${TAG}"
docker tag insure-copilot-fe:latest     "insure-copilot-fe:${TAG}"
docker tag insure-copilot-worker:latest "insure-copilot-worker:${TAG}"

echo "Images tagged: $TAG"
docker images --format "{{.Repository}}:{{.Tag}}" | grep "insure-copilot" | grep "$new_version"

# --------------------------------------------------------------------------
# 5. Deploy
# --------------------------------------------------------------------------
echo "Deploying..."
docker compose -f "$COMPOSE_FILE" up -d --no-build

echo ""
echo "Running containers:"
docker compose -f "$COMPOSE_FILE" ps

# --------------------------------------------------------------------------
# 6. Health check
# --------------------------------------------------------------------------
echo ""
echo "Waiting for backend health check..."

HEALTH_URL="http://localhost:48000/health"
MAX_ATTEMPTS=10
INTERVAL=10

for i in $(seq 1 $MAX_ATTEMPTS); do
  if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
    echo "Backend is healthy (attempt $i/$MAX_ATTEMPTS)"
    break
  fi
  if [ "$i" -eq "$MAX_ATTEMPTS" ]; then
    echo "ERROR: Backend failed to become healthy after $((MAX_ATTEMPTS * INTERVAL))s"
    exit 1
  fi
  echo "Attempt $i/$MAX_ATTEMPTS — not ready yet, retrying in ${INTERVAL}s..."
  sleep $INTERVAL
done

# Disable rollback trap — deploy succeeded
trap - ERR

# Write new version to .deployed_version for CI to pick up and create git tag
echo "$new_version" > "$REPO_ROOT/.deployed_version"

echo ""
echo "Deploy complete. Version: $new_version  Tag: $TAG"
