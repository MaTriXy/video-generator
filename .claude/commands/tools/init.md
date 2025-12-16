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
3. Run npm install in the visualise_video directory

Report the results to the user when complete.
