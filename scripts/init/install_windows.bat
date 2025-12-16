@echo off
setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   Windows Installation Script
echo   course-workflow Project Setup
echo ============================================================
echo.

:: Check if Python 3.13 is already installed and working
echo Checking for Python 3.13...

:: First, check if python command actually works (not just the Windows Store stub)
:: The Windows Store stub fails when trying to actually run Python
python -c "import sys; print(sys.version)" 2>nul | findstr /C:"3.13" >nul
if %errorlevel% equ 0 (
    echo [OK] Python 3.13 is already installed and working
    goto :install_packages
)

:: Check via py launcher - if py works but python doesn't, we need to fix PATH
py -3.13 --version 2>nul | findstr /C:"3.13" >nul
if %errorlevel% equ 0 (
    echo [INFO] Python 3.13 found via py launcher, configuring python command...

    :: Get Python path from py launcher and add to PATH
    for /f "tokens=*" %%i in ('py -3.13 -c "import sys; print(sys.executable)"') do set "PYTHON_EXE=%%i"
    for %%i in ("!PYTHON_EXE!") do set "PYTHON_INSTALL_PATH=%%~dpi"
    :: Remove trailing backslash
    if "!PYTHON_INSTALL_PATH:~-1!"=="\" set "PYTHON_INSTALL_PATH=!PYTHON_INSTALL_PATH:~0,-1!"

    echo Found Python at: !PYTHON_INSTALL_PATH!

    :: Add to current session PATH
    set "PATH=!PYTHON_INSTALL_PATH!;!PYTHON_INSTALL_PATH!\Scripts;%PATH%"

    :: Add to user PATH permanently
    echo Adding Python to user PATH...
    powershell -Command "$pythonPath = '!PYTHON_INSTALL_PATH!'; $scriptsPath = '!PYTHON_INSTALL_PATH!\Scripts'; $currentPath = [Environment]::GetEnvironmentVariable('Path', 'User'); if ($currentPath -notlike \"*$pythonPath*\") { [Environment]::SetEnvironmentVariable('Path', \"$pythonPath;$scriptsPath;$currentPath\", 'User'); Write-Host '[OK] Python added to user PATH' } else { Write-Host '[OK] Python already in PATH' }"

    goto :install_packages
)

echo Python 3.13 not found. Installing...

:: Create temp directory
set "TEMP_DIR=%TEMP%\python_install"
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

:: Download Python installer
set "PYTHON_VERSION=3.13.1"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-amd64.exe"
set "INSTALLER_PATH=%TEMP_DIR%\python-%PYTHON_VERSION%-amd64.exe"

echo.
echo ============================================================
echo   Downloading Python %PYTHON_VERSION%...
echo ============================================================
echo.

:: Use curl (available on Windows 10+) or PowerShell
where curl >nul 2>nul
if %errorlevel% equ 0 (
    curl -L -o "%INSTALLER_PATH%" "%PYTHON_URL%"
) else (
    powershell -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%INSTALLER_PATH%'"
)

if not exist "%INSTALLER_PATH%" (
    echo [ERROR] Failed to download Python installer
    echo Please download manually from: %PYTHON_URL%
    exit /b 1
)

echo [OK] Downloaded Python installer

:: Install Python silently
echo.
echo ============================================================
echo   Installing Python %PYTHON_VERSION%...
echo ============================================================
echo   (This may take a few minutes and require admin privileges)
echo.

"%INSTALLER_PATH%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=1 Include_test=0 DefaultAllUsersTargetDir="%LOCALAPPDATA%\Programs\Python\Python313"

if %errorlevel% neq 0 (
    echo [ERROR] Python installation failed
    echo Please run the installer manually: %INSTALLER_PATH%
    exit /b 1
)

echo [OK] Python installed successfully

:: Refresh environment variables
echo Refreshing environment...

:: Get the actual Python install path
set "PYTHON_USER_PATH=%LOCALAPPDATA%\Programs\Python\Python313"
set "PYTHON_SYSTEM_PATH=C:\Program Files\Python313"

:: Determine which path exists
if exist "%PYTHON_USER_PATH%\python.exe" (
    set "PYTHON_INSTALL_PATH=%PYTHON_USER_PATH%"
) else if exist "%PYTHON_SYSTEM_PATH%\python.exe" (
    set "PYTHON_INSTALL_PATH=%PYTHON_SYSTEM_PATH%"
) else (
    echo [WARNING] Could not find Python installation path
    set "PYTHON_INSTALL_PATH=%PYTHON_USER_PATH%"
)

:: Add Python to current session PATH (prepend so it takes priority over WindowsApps stub)
set "PATH=%PYTHON_INSTALL_PATH%;%PYTHON_INSTALL_PATH%\Scripts;%PATH%"

:: Also add to user PATH permanently using PowerShell
echo Adding Python to user PATH...
powershell -Command "$pythonPath = '%PYTHON_INSTALL_PATH%'; $scriptsPath = '%PYTHON_INSTALL_PATH%\Scripts'; $currentPath = [Environment]::GetEnvironmentVariable('Path', 'User'); if ($currentPath -notlike \"*$pythonPath*\") { [Environment]::SetEnvironmentVariable('Path', \"$pythonPath;$scriptsPath;$currentPath\", 'User'); Write-Host '[OK] Python added to user PATH' } else { Write-Host '[OK] Python already in PATH' }"

:: Disable Windows Store Python alias
echo Disabling Windows Store Python alias...
powershell -Command "if (Test-Path '%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe') { Write-Host '[INFO] Note: Windows Store Python stub exists. The real Python is now prioritized in PATH.' }"

:install_packages
echo.
echo ============================================================
echo   Installing pip packages...
echo ============================================================
echo.

:: Always use python command
set "PYTHON_CMD=python"

:: Upgrade pip
echo Upgrading pip...
%PYTHON_CMD% -m pip install --upgrade pip

:: Get the script directory and project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."

:: Install requirements
echo Installing packages from requirements.txt...
%PYTHON_CMD% -m pip install -r "%PROJECT_ROOT%\requirements.txt"

if %errorlevel% neq 0 (
    echo [WARNING] Some packages may not have installed correctly
)

:install_npm
echo.
echo ============================================================
echo   Installing npm packages...
echo ============================================================
echo.

:: Check if Node.js is installed
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] Node.js is not installed
    echo Please install from: https://nodejs.org/
    goto :verify
)

:: Install npm packages
cd /d "%PROJECT_ROOT%\visualise_video"
if exist "package.json" (
    echo Running npm install in visualise_video...
    call npm install
    if %errorlevel% equ 0 (
        echo [OK] npm packages installed
    ) else (
        echo [WARNING] npm install may have failed
    )
) else (
    echo [WARNING] package.json not found in visualise_video
)

:verify
echo.
echo ============================================================
echo   Verifying Installation
echo ============================================================
echo.

:: Verify Python
python --version 2>nul
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo [OK] %%i
) else (
    echo [ERROR] Python not working - please restart your terminal and try again
)

:: Verify pip
python -m pip --version >nul 2>nul
if %errorlevel% equ 0 (
    echo [OK] pip is working
) else (
    echo [ERROR] pip not working
)

:: Verify Node
where node >nul 2>nul
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('node --version 2^>^&1') do echo [OK] Node.js %%i
) else (
    echo [WARNING] Node.js not installed
)

echo.
echo ============================================================
echo   Setup Complete!
echo ============================================================
echo.
echo To start the video player:
echo   cd visualise_video ^&^& npm run dev
echo.
echo Or use: /tools:run-player
echo.

endlocal
exit /b 0
