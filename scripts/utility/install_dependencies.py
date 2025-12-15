import subprocess
import sys
import platform
import argparse


def run_command(command: list, description: str) -> bool:
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"Command: {' '.join(command)}")
    print(f"{'='*60}\n")

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False  # Don't raise exception, we'll handle the return code
        )

        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        if result.returncode == 0:
            print(f"\n✓ {description} completed successfully")
            return True
        else:
            print(f"\n✗ {description} failed with exit code {result.returncode}")
            return False

    except FileNotFoundError:
        print(f"\n✗ Error: Command not found: {command[0]}")
        print(f"  Make sure {command[0]} is installed and in your PATH")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False


def install_ffmpeg() -> bool:
    """Install ffmpeg using the appropriate package manager for the platform."""

    system = platform.system()

    if system == "Windows":
        # Use winget on Windows
        command = ["winget", "install", "ffmpeg"]
        return run_command(command, "Installing ffmpeg (Windows)")

    elif system == "Darwin":
        # Use Homebrew on macOS
        command = ["brew", "install", "ffmpeg"]
        return run_command(command, "Installing ffmpeg (macOS)")

    elif system == "Linux":
        # Use apt on Linux (Debian/Ubuntu)
        print("\n⚠ Attempting to install ffmpeg using apt (Debian/Ubuntu)")
        print("  If you're using a different Linux distribution, please install manually")
        command = ["sudo", "apt", "install", "-y", "ffmpeg"]
        return run_command(command, "Installing ffmpeg (Linux)")

    else:
        print(f"\n✗ Unsupported platform: {system}")
        print("  Please install ffmpeg manually")
        return False


def install_python_requirements() -> bool:
    """Install Python dependencies from requirements.txt."""
    command = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
    return run_command(command, "Installing Python requirements from requirements.txt")


def install_playwright() -> bool:
    command = ["playwright", "install"]
    return run_command(command, "Installing Playwright browsers")


def main():
    parser = argparse.ArgumentParser(
        description='Install dependencies required for video recording',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/install_dependencies.py
  python scripts/install_dependencies.py --skip-requirements
        """
    )

    parser.add_argument('--skip-requirements', action='store_true',
                        help='Skip installing Python requirements from requirements.txt')

    args = parser.parse_args()

    print("\n" + "="*60)
    print("Dependencies Installation")
    print("="*60)

    results = []
    step = 1
    total_steps = 3 if not args.skip_requirements else 2

    # Install Python requirements (if not skipped)
    if not args.skip_requirements:
        print(f"\n[{step}/{total_steps}] Installing Python requirements...")
        requirements_success = install_python_requirements()
        results.append(("Python requirements", requirements_success))
        step += 1
    else:
        print("\n⊘ Skipping Python requirements installation")

    # Install ffmpeg
    print(f"\n[{step}/{total_steps}] Installing ffmpeg...")
    ffmpeg_success = install_ffmpeg()
    results.append(("ffmpeg", ffmpeg_success))
    step += 1

    # Install Playwright browsers
    print(f"\n[{step}/{total_steps}] Installing Playwright browsers...")
    playwright_success = install_playwright()
    results.append(("Playwright browsers", playwright_success))

    # Summary
    print("\n" + "="*60)
    print("Installation Summary")
    print("="*60)

    all_success = True
    for name, success in results:
        status = "✓" if success else "✗"
        print(f"{status} {name}: {'Installed' if success else 'Failed'}")
        if not success:
            all_success = False

    print("="*60)

    if all_success:
        print("\n✓ All dependencies installed successfully!")
        print("\nYou can now run the video recording script:")
        print("  python scripts/record_video.py -l 1 -m 6 -v 1")
        sys.exit(0)
    else:
        print("\n✗ Some dependencies failed to install")
        print("  Please check the error messages above and install manually")
        sys.exit(1)


if __name__ == '__main__':
    main()
