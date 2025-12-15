#!/bin/bash

set -e

echo ""
echo "============================================================"
echo "  Outputs Repository Setup - Linux"
echo "============================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_ok() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if creator_name argument is provided
if [ -z "$1" ]; then
    print_error "Creator name is required!"
    echo "Usage: ./setup_output_linux.sh <creator_name>"
    exit 1
fi

CREATOR_NAME="$1"
echo "Creator name: $CREATOR_NAME"
echo ""

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUTS_DIR="$PROJECT_ROOT/Outputs"
REPO_URL="https://github.com/outscal/video-output.git"

# Check if Outputs folder exists and is a git repo
if [ -d "$OUTPUTS_DIR/.git" ]; then
    print_ok "Outputs folder exists and is a git repository"
    cd "$OUTPUTS_DIR"
else
    echo "Outputs folder not found or not a git repo. Cloning..."

    # Remove Outputs folder if it exists but isn't a git repo
    if [ -d "$OUTPUTS_DIR" ]; then
        echo "Removing existing non-git Outputs folder..."
        rm -rf "$OUTPUTS_DIR"
    fi

    # Clone the repository
    echo "Cloning $REPO_URL into Outputs..."
    cd "$PROJECT_ROOT"
    git clone "$REPO_URL" Outputs

    if [ $? -ne 0 ]; then
        print_error "Failed to clone the Outputs repository check if you have access to the Outputs"
        exit 1
    fi

    print_ok "Outputs repository cloned successfully"
    cd "$OUTPUTS_DIR"
fi

# Fetch all remote branches
echo ""
echo "Fetching remote branches..."
git fetch origin

# Check if the branch already exists (local or remote)
echo ""
echo "Checking if branch '$CREATOR_NAME' already exists..."

# Check local branches
if git show-ref --verify --quiet "refs/heads/$CREATOR_NAME"; then
    print_error "Branch '$CREATOR_NAME' already exists locally!"
    echo "Please choose a different creator name."
    exit 1
fi

# Check remote branches
if git ls-remote --heads origin "$CREATOR_NAME" | grep -q "$CREATOR_NAME"; then
    print_error "Branch '$CREATOR_NAME' already exists on remote!"
    echo "Please choose a different creator name."
    exit 1
fi

print_ok "Branch name '$CREATOR_NAME' is available"

# Create the new branch from main
echo ""
echo "Creating branch '$CREATOR_NAME'..."
git checkout main 2>/dev/null || git checkout master 2>/dev/null
git pull origin main 2>/dev/null || git pull origin master 2>/dev/null
git checkout -b "$CREATOR_NAME"

if [ $? -ne 0 ]; then
    print_error "Failed to create branch '$CREATOR_NAME'"
    exit 1
fi

print_ok "Branch '$CREATOR_NAME' created successfully"

# Push the branch to remote
echo ""
echo "Publishing branch '$CREATOR_NAME' to remote..."
git push -u origin "$CREATOR_NAME"

if [ $? -ne 0 ]; then
    print_error "Failed to publish branch '$CREATOR_NAME' to remote"
    exit 1
fi

echo ""
echo "============================================================"
echo "  Outputs Repository Setup Complete!"
echo "============================================================"
echo ""
print_ok "Branch '$CREATOR_NAME' has been created and published"
print_ok "You are now on branch '$CREATOR_NAME' in the Outputs folder"
echo ""
