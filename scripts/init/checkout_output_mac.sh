#!/bin/bash

set -e

echo ""
echo "============================================================"
echo "  Outputs Repository Checkout - macOS"
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

# Check if branch argument is provided
if [ -z "$1" ]; then
    print_error "Branch name is required!"
    echo "Usage: ./checkout_output_mac.sh <branch_name>"
    exit 1
fi

BRANCH_NAME="$1"
echo "Branch name: $BRANCH_NAME"
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
        print_error "Failed to clone the Outputs repository. Check if you have access."
        exit 1
    fi

    print_ok "Outputs repository cloned successfully"
    cd "$OUTPUTS_DIR"
fi

# Fetch all remote branches
echo ""
echo "Fetching remote branches..."
git fetch origin

# Check if the branch exists on remote
echo ""
echo "Checking if branch '$BRANCH_NAME' exists on remote..."

if ! git ls-remote --heads origin "$BRANCH_NAME" | grep -q "$BRANCH_NAME"; then
    print_error "Branch '$BRANCH_NAME' does not exist on remote!"
    echo "Please provide a valid branch name."
    exit 1
fi

print_ok "Branch '$BRANCH_NAME' found on remote"

# Checkout to the branch
echo ""
echo "Checking out to branch '$BRANCH_NAME'..."

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" == "$BRANCH_NAME" ]; then
    print_ok "Already on branch '$BRANCH_NAME'"
    git pull origin "$BRANCH_NAME"
else
    # Check if branch exists locally
    if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
        # Branch exists locally, just checkout
        git checkout "$BRANCH_NAME"
        git pull origin "$BRANCH_NAME"
    else
        # Branch doesn't exist locally, checkout from remote
        git checkout -b "$BRANCH_NAME" "origin/$BRANCH_NAME"
    fi
fi

if [ $? -ne 0 ]; then
    print_error "Failed to checkout to branch '$BRANCH_NAME'"
    exit 1
fi

echo ""
echo "============================================================"
echo "  Outputs Repository Checkout Complete!"
echo "============================================================"
echo ""
print_ok "You are now on branch '$BRANCH_NAME' in the Outputs folder"
echo ""
