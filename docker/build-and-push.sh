#!/bin/bash
# Build Elzar image and push to local registry
#
# Usage:
#   ./build-and-push.sh              # Build and push as 'latest'
#   ./build-and-push.sh v1.1.0       # Build and push with specific tag

set -e

# Configuration
REGISTRY="${REGISTRY:-localhost:5000}"
IMAGE_NAME="elzar"
TAG="${1:-latest}"

# Full image references
LOCAL_TAG="${IMAGE_NAME}:${TAG}"
REMOTE_TAG="${REGISTRY}/${IMAGE_NAME}:${TAG}"

echo "=============================================="
echo "  Building Elzar Docker Image"
echo "=============================================="
echo "  Registry: ${REGISTRY}"
echo "  Image:    ${REMOTE_TAG}"
echo "=============================================="

# Get the directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Resolve symlink to get actual source directory
SOURCE_DIR="$(readlink -f "${SCRIPT_DIR}")"
PROJECT_ROOT="$(dirname "${SOURCE_DIR}")"

echo ""
echo "Building from: ${PROJECT_ROOT}"
echo ""

# Build the image
docker build \
    -t "${LOCAL_TAG}" \
    -t "${REMOTE_TAG}" \
    -f "${SOURCE_DIR}/Dockerfile" \
    "${PROJECT_ROOT}"

echo ""
echo "Build complete!"
echo ""

# Check if registry is running
if ! curl -s "http://${REGISTRY}/v2/" > /dev/null 2>&1; then
    echo "WARNING: Registry at ${REGISTRY} is not reachable."
    echo "Start the registry first:"
    echo "  cd /home/bironfamily/Documents/Project\\ Workspaces/docker-images"
    echo "  docker compose up -d"
    echo ""
    echo "Image built locally as: ${LOCAL_TAG}"
    exit 0
fi

# Push to registry
echo "Pushing to registry..."
docker push "${REMOTE_TAG}"

# Also push as 'latest' if we used a version tag
if [ "${TAG}" != "latest" ]; then
    LATEST_TAG="${REGISTRY}/${IMAGE_NAME}:latest"
    docker tag "${LOCAL_TAG}" "${LATEST_TAG}"
    docker push "${LATEST_TAG}"
    echo "Also pushed as: ${LATEST_TAG}"
fi

echo ""
echo "=============================================="
echo "  Done! Image available at:"
echo "  ${REMOTE_TAG}"
echo "=============================================="
echo ""
echo "To use on your server, pull with:"
echo "  docker pull ${REMOTE_TAG}"
