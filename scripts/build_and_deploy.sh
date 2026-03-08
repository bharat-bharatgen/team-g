#!/usr/bin/env bash
# build_and_deploy.sh
#
# Usage (local):  ./scripts/build_and_deploy.sh [patch|minor|major]
# Usage (CI):     called by .github/workflows/deploy.yml on push to main
#
# Steps:
#   1. Bump VERSION file (patch by default)
#   2. Build Docker images tagged as <version>_<commit-hash>
#   3. Deploy with docker compose (pull new images and restart)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION_FILE="$REPO_ROOT/VERSION"
COMPOSE_FILE="$REPO_ROOT/docker-compose.yml"

# --------------------------------------------------------------------------
# 1. Bump version
# --------------------------------------------------------------------------
BUMP="${1:-patch}"   # patch | minor | major

current="$(cat "$VERSION_FILE" | tr -d '[:space:]')"
IFS='.' read -r major minor patch <<< "$current"

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
echo "$new_version" > "$VERSION_FILE"
echo "Version bumped: $current → $new_version"

# --------------------------------------------------------------------------
# 2. Build images
# --------------------------------------------------------------------------
commit_hash="$(git -C "$REPO_ROOT" rev-parse HEAD)"
TAG="${new_version}_${commit_hash}"

echo "Building images with tag: $TAG"

docker compose -f "$COMPOSE_FILE" build \
  --build-arg VITE_API_BASE_URL=/api/v1 \
  --build-arg VITE_APP_NAME=InsureCopilot

# Tag the built images
docker tag insure-copilot-BE  "insure-copilot-BE:${TAG}"
docker tag insure-copilot-FE  "insure-copilot-FE:${TAG}"
# Worker uses the same image as backend
docker tag insure-copilot-BE  "insure-copilot-WORKER:${TAG}"

echo "Images tagged:"
docker images | grep "insure-copilot" | grep "$new_version"

# --------------------------------------------------------------------------
# 3. Deploy
# --------------------------------------------------------------------------
echo "Deploying..."

docker compose -f "$COMPOSE_FILE" up -d --no-build

echo ""
echo "Deploy complete. Running containers:"
docker compose -f "$COMPOSE_FILE" ps

echo ""
echo "Done. Version: $new_version  Tag: $TAG"
