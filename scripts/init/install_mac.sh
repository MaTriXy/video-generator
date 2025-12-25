#!/bin/bash

set -e

echo ""
echo "============================================================"
echo "  macOS Installation Script"
echo "  course-workflow Project Setup"
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

print_step() {
    echo ""
    echo "============================================================"
    echo "  $1"
    echo "============================================================"
    echo ""
}

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Check if Homebrew is installed
check_homebrew() {
    if command -v brew &> /dev/null; then
        print_ok "Homebrew is installed: $(brew --version | head -1)"
        return 0
    else
        return 1
    fi
}

# Install Homebrew
install_homebrew() {
    print_step "Installing Homebrew..."

    echo "Homebrew is required for this installation."
    echo ""
    echo "To install Homebrew, run:"
    echo '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    echo ""
    echo "After installing Homebrew, run this script again."
    exit 1
}

# Check if Python 3.13 is installed
check_python() {
    # First check if 'python' command works and is 3.13
    if command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version 2>&1)
        if [[ "$PYTHON_VERSION" == *"3.13"* ]]; then
            print_ok "Python 3.13 is already installed and 'python' command works: $PYTHON_VERSION"
            PYTHON_CMD="python"
            return 0
        fi
    fi

    if command -v python3.13 &> /dev/null; then
        print_ok "Python 3.13 is already installed: $(python3.13 --version)"
        PYTHON_CMD="python3.13"
        return 0
    fi

    # Check Homebrew Python paths
    for prefix in "/opt/homebrew" "/usr/local"; do
        if [ -x "$prefix/bin/python3.13" ]; then
            print_ok "Python 3.13 found at $prefix/bin/python3.13"
            PYTHON_CMD="$prefix/bin/python3.13"
            return 0
        fi
    done

    # Check default python3
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1)
        if [[ "$PYTHON_VERSION" == *"3.13"* ]]; then
            print_ok "Python 3.13 is already installed: $PYTHON_VERSION"
            PYTHON_CMD="python3"
            return 0
        fi
    fi

    return 1
}

# Setup python command alias
setup_python_alias() {
    print_step "Setting up 'python' command..."

    # Check if python already points to python3.13
    if command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version 2>&1)
        if [[ "$PYTHON_VERSION" == *"3.13"* ]]; then
            print_ok "'python' command already works"
            PYTHON_CMD="python"
            return 0
        fi
    fi

    # Determine the actual Python 3.13 path
    local PYTHON_PATH=""
    if command -v python3.13 &> /dev/null; then
        PYTHON_PATH=$(which python3.13)
    elif [ -x "/opt/homebrew/bin/python3.13" ]; then
        PYTHON_PATH="/opt/homebrew/bin/python3.13"
    elif [ -x "/usr/local/bin/python3.13" ]; then
        PYTHON_PATH="/usr/local/bin/python3.13"
    elif command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1)
        if [[ "$PYTHON_VERSION" == *"3.13"* ]]; then
            PYTHON_PATH=$(which python3)
        fi
    fi

    if [ -z "$PYTHON_PATH" ]; then
        print_warning "Could not find Python 3.13 to create alias"
        return 1
    fi

    # Add alias to shell config
    local SHELL_RC=""
    if [ -f "$HOME/.zshrc" ]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -f "$HOME/.bashrc" ]; then
        SHELL_RC="$HOME/.bashrc"
    elif [ -f "$HOME/.bash_profile" ]; then
        SHELL_RC="$HOME/.bash_profile"
    fi

    if [ -n "$SHELL_RC" ]; then
        # Check if alias already exists
        if ! grep -q "alias python=" "$SHELL_RC" 2>/dev/null; then
            echo "" >> "$SHELL_RC"
            echo "# Python alias added by course-workflow installer" >> "$SHELL_RC"
            echo "alias python='$PYTHON_PATH'" >> "$SHELL_RC"
            print_ok "Added 'python' alias to $SHELL_RC"
            echo "Run 'source $SHELL_RC' or restart your terminal to use 'python' command"
        else
            print_ok "'python' alias already exists in $SHELL_RC"
        fi
    fi

    # Also create symlink in ~/.local/bin if possible
    mkdir -p "$HOME/.local/bin"
    if [ ! -f "$HOME/.local/bin/python" ]; then
        ln -sf "$PYTHON_PATH" "$HOME/.local/bin/python"
        print_ok "Created symlink: ~/.local/bin/python -> $PYTHON_PATH"

        # Add ~/.local/bin to PATH if not already there
        if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
            export PATH="$HOME/.local/bin:$PATH"
            if [ -n "$SHELL_RC" ] && ! grep -q 'PATH.*\.local/bin' "$SHELL_RC" 2>/dev/null; then
                echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
                print_ok "Added ~/.local/bin to PATH in $SHELL_RC"
            fi
        fi
    fi

    # Update PYTHON_CMD for current session
    if [ -x "$HOME/.local/bin/python" ]; then
        PYTHON_CMD="$HOME/.local/bin/python"
    fi

    return 0
}

# Install Python via Homebrew
install_python() {
    print_step "Installing Python 3.13 via Homebrew..."

    brew install python@3.13

    # Link it
    brew link python@3.13 2>/dev/null || true

    # Find the installed Python
    if command -v python3.13 &> /dev/null; then
        PYTHON_CMD="python3.13"
    elif [ -x "/opt/homebrew/bin/python3.13" ]; then
        PYTHON_CMD="/opt/homebrew/bin/python3.13"
    elif [ -x "/usr/local/bin/python3.13" ]; then
        PYTHON_CMD="/usr/local/bin/python3.13"
    else
        print_error "Python 3.13 installation failed"
        return 1
    fi

    print_ok "Python 3.13 installed successfully"
    return 0
}

# Main installation flow
main() {
    # Check for Homebrew
    if ! check_homebrew; then
        install_homebrew
    fi

    # Install Python if needed
    if ! check_python; then
        install_python || exit 1
    fi

    # Setup 'python' command alias/symlink so 'python' works
    setup_python_alias

    # Upgrade pip
    print_step "Setting up pip..."
    $PYTHON_CMD -m pip install --upgrade pip

    # Install pip packages
    print_step "Installing pip packages..."

    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        echo "Installing packages from requirements.txt..."
        $PYTHON_CMD -m pip install -r "$PROJECT_ROOT/requirements.txt"
        if [ $? -eq 0 ]; then
            print_ok "pip packages installed successfully"
        else
            print_warning "Some pip packages may not have installed correctly"
        fi
    else
        print_error "requirements.txt not found at $PROJECT_ROOT/requirements.txt"
    fi

    # Install npm packages
    print_step "Installing npm packages..."

    if ! command -v node &> /dev/null; then
        print_warning "Node.js is not installed"
        echo "Install with: brew install node"
        echo "Or download from: https://nodejs.org/"
    else
        print_ok "Node.js is installed: $(node --version)"

        # Install npm packages in root directory
        if [ -f "$PROJECT_ROOT/package.json" ]; then
            echo "Running npm install in root directory..."
            cd "$PROJECT_ROOT"
            npm install
            if [ $? -eq 0 ]; then
                print_ok "Root npm packages installed successfully"
            else
                print_warning "Root npm install may have failed"
            fi
        fi

    fi

    # Verification
    print_step "Verifying Installation"

    echo ""
    $PYTHON_CMD --version && print_ok "Python: $($PYTHON_CMD --version)"
    $PYTHON_CMD -m pip --version > /dev/null && print_ok "pip is working"

    if command -v node &> /dev/null; then
        print_ok "Node.js: $(node --version)"
    else
        print_warning "Node.js not installed"
    fi

    print_step "Setup Complete!"
}

# Run main
main "$@"
