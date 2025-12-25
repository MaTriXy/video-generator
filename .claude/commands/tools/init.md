---
description: Install all project dependencies (Python, pip packages, npm packages)
allowed-tools: Bash
model: haiku

---

Run the installation script:

**For Windows:**
```bash
scripts\init\install_windows.bat
```

**For Linux:**
```bash
chmod +x scripts/init/install_linux.sh && ./scripts/init/install_linux.sh
```

**For macOS:**
```bash
chmod +x scripts/init/install_mac.sh && ./scripts/init/install_mac.sh
```

The installation script will:
1. Install Python 3.13 if not already installed
2. Install all pip packages from requirements.txt

Report the results to the user when complete.

After installation completes successfully:
1. Copy `.env.template` to `.env` in the project root folder (if `.env` doesn't already exist)

**Ask the user to do:**
1. Visit: https://production2.outscal.com/v2/get-video-generation-api-key
2. Register for an account (or login if already registered) to get their API key
3. Open the `.env` file in the project root directory
4. Paste their API key in the appropriate field

Wait for the user to confirm they have completed the API key setup before finishing.
