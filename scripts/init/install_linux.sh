#!/bin/bash

set -e

echo ""
echo "============================================================"
echo "  Linux Installation Script"
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

# Detect Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO_ID="${ID}"
        DISTRO_LIKE="${ID_LIKE:-}"
    else
        DISTRO_ID="unknown"
        DISTRO_LIKE=""
    fi

    # Normalize to package manager type
    case "$DISTRO_ID" in
        ubuntu|debian|pop|linuxmint|elementary)
            echo "debian"
            ;;
        fedora|rhel|centos|rocky|alma)
            echo "fedora"
            ;;
        arch|manjaro|endeavouros)
            echo "arch"
            ;;
        opensuse*|suse)
            echo "suse"
            ;;
        *)
            # Check ID_LIKE as fallback
            if [[ "$DISTRO_LIKE" == *"debian"* ]] || [[ "$DISTRO_LIKE" == *"ubuntu"* ]]; then
                echo "debian"
            elif [[ "$DISTRO_LIKE" == *"fedora"* ]] || [[ "$DISTRO_LIKE" == *"rhel"* ]]; then
                echo "fedora"
            elif [[ "$DISTRO_LIKE" == *"arch"* ]]; then
                echo "arch"
            else
                echo "unknown"
            fi
            ;;
    esac
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
    elif command -v python3 &> /dev/null; then
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
    if [ -n "$ZSH_VERSION" ] || [ -f "$HOME/.zshrc" ]; then
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

# Install Python on Debian/Ubuntu
install_python_debian() {
    print_step "Installing Python 3.13 on Debian/Ubuntu..."

    echo "Adding deadsnakes PPA..."
    sudo apt update
    sudo apt install -y software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa || print_warning "Could not add deadsnakes PPA"
    sudo apt update

    echo "Installing Python 3.13..."
    sudo apt install -y python3.13 python3.13-venv python3.13-dev python3-pip

    if command -v python3.13 &> /dev/null; then
        print_ok "Python 3.13 installed successfully"
        PYTHON_CMD="python3.13"
        return 0
    else
        print_error "Failed to install Python 3.13"
        return 1
    fi
}

# Install Python on Fedora/RHEL
install_python_fedora() {
    print_step "Installing Python 3.13 on Fedora/RHEL..."

    sudo dnf install -y python3.13 python3.13-pip python3.13-devel

    if command -v python3.13 &> /dev/null; then
        print_ok "Python 3.13 installed successfully"
        PYTHON_CMD="python3.13"
        return 0
    else
        print_error "Failed to install Python 3.13"
        return 1
    fi
}

# Install Python on Arch
install_python_arch() {
    print_step "Installing Python on Arch Linux..."

    sudo pacman -S --noconfirm python python-pip

    if command -v python &> /dev/null; then
        print_ok "Python installed successfully: $(python --version)"
        PYTHON_CMD="python"
        return 0
    else
        print_error "Failed to install Python"
        return 1
    fi
}

# Install Python on openSUSE
install_python_suse() {
    print_step "Installing Python 3.13 on openSUSE..."

    sudo zypper install -y python313 python313-pip python313-devel

    if command -v python3.13 &> /dev/null; then
        print_ok "Python 3.13 installed successfully"
        PYTHON_CMD="python3.13"
        return 0
    else
        print_error "Failed to install Python 3.13"
        return 1
    fi
}

# Main installation flow
main() {
    # Detect distribution
    DISTRO=$(detect_distro)
    echo "Detected distribution type: $DISTRO"

    if [ "$DISTRO" == "unknown" ]; then
        print_error "Unsupported Linux distribution"
        echo "Please install Python 3.13 manually and run this script again"
        exit 1
    fi

    # Install Python if needed
    if ! check_python; then
        case "$DISTRO" in
            debian)
                install_python_debian || exit 1
                ;;
            fedora)
                install_python_fedora || exit 1
                ;;
            arch)
                install_python_arch || exit 1
                ;;
            suse)
                install_python_suse || exit 1
                ;;
        esac
    fi

    # Setup 'python' command alias/symlink so 'python' works
    setup_python_alias

    # Ensure pip is available
    print_step "Setting up pip..."
    $PYTHON_CMD -m ensurepip --upgrade 2>/dev/null || true
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
        echo "Please install from: https://nodejs.org/"
    else
        print_ok "Node.js is installed: $(node --version)"

        if [ -d "$PROJECT_ROOT/visualise_video" ] && [ -f "$PROJECT_ROOT/visualise_video/package.json" ]; then
            echo "Running npm install in visualise_video..."
            cd "$PROJECT_ROOT/visualise_video"
            npm install
            if [ $? -eq 0 ]; then
                print_ok "npm packages installed successfully"
            else
                print_warning "npm install may have failed"
            fi
        else
            print_warning "visualise_video/package.json not found"
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

    echo "To start the video player:"
    echo "  cd visualise_video && npm run dev"
    echo ""
    echo "Or use: /tools:run-player"
    echo ""
}

# Run main
main "$@"
