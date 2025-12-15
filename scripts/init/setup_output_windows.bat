@echo off
setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   Outputs Repository Setup - Windows
echo ============================================================
echo.

:: Check if creator_name argument is provided
if "%~1"=="" (
    echo [ERROR] Creator name is required!
    echo Usage: setup_output_windows.bat ^<creator_name^>
    exit /b 1
)

set "CREATOR_NAME=%~1"
echo Creator name: %CREATOR_NAME%
echo.

:: Get the script directory and project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
set "OUTPUTS_DIR=%PROJECT_ROOT%\Outputs"
set "REPO_URL=https://github.com/outscal/video-output.git"

:: Check if Outputs folder exists and is a git repo
if exist "%OUTPUTS_DIR%\.git" (
    echo [OK] Outputs folder exists and is a git repository
    cd /d "%OUTPUTS_DIR%"
) else (
    echo Outputs folder not found or not a git repo. Cloning...

    :: Remove Outputs folder if it exists but isn't a git repo
    if exist "%OUTPUTS_DIR%" (
        echo Removing existing non-git Outputs folder...
        rmdir /s /q "%OUTPUTS_DIR%"
    )

    :: Clone the repository
    echo Cloning %REPO_URL% into Outputs...
    cd /d "%PROJECT_ROOT%"
    git clone "%REPO_URL%" Outputs

    if %errorlevel% neq 0 (
        echo [ERROR] Failed to clone the Outputs repository
        exit /b 1
    )

    echo [OK] Outputs repository cloned successfully
    cd /d "%OUTPUTS_DIR%"
)

:: Fetch all remote branches
echo.
echo Fetching remote branches...
git fetch origin

:: Check if the branch already exists (local or remote)
echo.
echo Checking if branch '%CREATOR_NAME%' already exists...

:: Check local branches
git show-ref --verify --quiet refs/heads/%CREATOR_NAME%
if %errorlevel% equ 0 (
    echo [ERROR] Branch '%CREATOR_NAME%' already exists locally!
    echo Please choose a different creator name.
    exit /b 1
)

:: Check remote branches
git ls-remote --heads origin %CREATOR_NAME% | findstr %CREATOR_NAME% >nul
if %errorlevel% equ 0 (
    echo [ERROR] Branch '%CREATOR_NAME%' already exists on remote!
    echo Please choose a different creator name.
    exit /b 1
)

echo [OK] Branch name '%CREATOR_NAME%' is available

:: Create the new branch from main
echo.
echo Creating branch '%CREATOR_NAME%'...
git checkout main 2>nul || git checkout master 2>nul
git pull origin main 2>nul || git pull origin master 2>nul
git checkout -b %CREATOR_NAME%

if %errorlevel% neq 0 (
    echo [ERROR] Failed to create branch '%CREATOR_NAME%'
    exit /b 1
)

echo [OK] Branch '%CREATOR_NAME%' created successfully

:: Push the branch to remote
echo.
echo Publishing branch '%CREATOR_NAME%' to remote...
git push -u origin %CREATOR_NAME%

if %errorlevel% neq 0 (
    echo [ERROR] Failed to publish branch '%CREATOR_NAME%' to remote
    exit /b 1
)

echo.
echo ============================================================
echo   Outputs Repository Setup Complete!
echo ============================================================
echo.
echo [OK] Branch '%CREATOR_NAME%' has been created and published
echo [OK] You are now on branch '%CREATOR_NAME%' in the Outputs folder
echo.

endlocal
exit /b 0
