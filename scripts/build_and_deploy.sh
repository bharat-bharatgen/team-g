#!/usr/bin/env bash
# build_and_deploy.sh
#
# Usage (local):  ./scripts/build_and_deploy.sh [patch|minor|major]
# Usage (CI):     called by .github/workflows/deploy.yml on workflow_dispatch
#
# Steps:
#   1. Validate VERSION file
#   2. Save previous images for rollback
#   3. Build Docker images
#   4. Bump VERSION (after successful build, so tag hash matches deployed commit)
#   5. Tag built images as <version>_<short-commit-hash>
#   6. Deploy with docker compose
#   7. Health check — verify backend is up
#   Rollback: if any step fails, restore previous images and restart

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION_FILE="$REPO_ROOT/VERSION"
COMPOSE_FILE="$REPO_ROOT/docker-compose.yml"

# --------------------------------------------------------------------------
# 1. Validate VERSION and compute new version (don't write yet)
# --------------------------------------------------------------------------
BUMP="${1:-patch}"   # patch | minor | major

current="$(cat "$VERSION_FILE" | tr -d '[:space:]')"
IFS='.' read -r major minor patch <<< "$current"

# Validate that version components are integers
if ! [[ "$major" =~ ^[0-9]+$ ]] || ! [[ "$minor" =~ ^[0-9]+$ ]] || ! [[ "$patch" =~ ^[0-9]+$ ]]; then
  echo "ERROR: VERSION file contains invalid version '$current'. Expected format: X.Y.Z"
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
prev_backend="$(docker images insure-copilot-BE:latest --format '{{.ID}}' 2>/dev/null || true)"
prev_frontend="$(docker images insure-copilot-FE:latest --format '{{.ID}}' 2>/dev/null || true)"
prev_worker="$(docker images insure-copilot-WORKER:latest --format '{{.ID}}' 2>/dev/null || true)"

rollback() {
  echo ""
  echo "ERROR: Deploy failed. Rolling back to previous images..."

  # Restore VERSION file
  echo "$current" > "$VERSION_FILE"

  # Retag previous images back to latest if they existed
  if [ -n "$prev_backend" ];  then docker tag "$prev_backend"  insure-copilot-BE:latest;     fi
  if [ -n "$prev_frontend" ]; then docker tag "$prev_frontend" insure-copilot-FE:latest;     fi
  if [ -n "$prev_worker" ];   then docker tag "$prev_worker"   insure-copilot-WORKER:latest; fi

  # Restart with previous images
  docker compose -f "$COMPOSE_FILE" up -d --no-build
  echo "Rollback complete. Running previous version: $current"
}

trap rollback ERR

# --------------------------------------------------------------------------
# 3. Build images
# --------------------------------------------------------------------------
VITE_API_BASE_URL="${VITE_API_BASE_URL:-/api/v1}"
VITE_APP_NAME="${VITE_APP_NAME:-InsureCopilot}"

echo "Building images (VITE_API_BASE_URL: $VITE_API_BASE_URL)..."

docker compose -f "$COMPOSE_FILE" build \
  --build-arg VITE_API_BASE_URL="$VITE_API_BASE_URL" \
  --build-arg VITE_APP_NAME="$VITE_APP_NAME"

# --------------------------------------------------------------------------
# 4. Bump VERSION now — build succeeded, hash is stable
# --------------------------------------------------------------------------
echo "$new_version" > "$VERSION_FILE"
echo "Version bumped: $current → $new_version"

# --------------------------------------------------------------------------
# 5. Tag built images with versioned snapshot tag
# --------------------------------------------------------------------------
short_hash="$(git -C "$REPO_ROOT" rev-parse --short HEAD)"
TAG="${new_version}_${short_hash}"

docker tag insure-copilot-BE:latest     "insure-copilot-BE:${TAG}"
docker tag insure-copilot-FE:latest     "insure-copilot-FE:${TAG}"
docker tag insure-copilot-WORKER:latest "insure-copilot-WORKER:${TAG}"

echo "Images tagged: $TAG"
docker images --format "{{.Repository}}:{{.Tag}}" | grep "insure-copilot" | grep "$new_version"

# --------------------------------------------------------------------------
# 6. Deploy
# --------------------------------------------------------------------------
echo "Deploying..."
docker compose -f "$COMPOSE_FILE" up -d --no-build

echo ""
echo "Running containers:"
docker compose -f "$COMPOSE_FILE" ps

# --------------------------------------------------------------------------
# 7. Health check
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

echo ""
echo "Deploy complete. Version: $new_version  Tag: $TAG"
