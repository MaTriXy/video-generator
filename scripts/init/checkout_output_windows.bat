@echo off
setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   Outputs Repository Checkout - Windows
echo ============================================================
echo.

:: Check if branch argument is provided
if "%~1"=="" (
    echo [ERROR] Branch name is required!
    echo Usage: checkout_output_windows.bat ^<branch_name^>
    exit /b 1
)

set "BRANCH_NAME=%~1"
echo Branch name: %BRANCH_NAME%
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

:: Check if the branch exists on remote
echo.
echo Checking if branch '%BRANCH_NAME%' exists on remote...

git ls-remote --heads origin %BRANCH_NAME% | findstr %BRANCH_NAME% >nul
if %errorlevel% neq 0 (
    echo [ERROR] Branch '%BRANCH_NAME%' does not exist on remote!
    echo Please provide a valid branch name.
    exit /b 1
)

echo [OK] Branch '%BRANCH_NAME%' found on remote

:: Checkout to the branch
echo.
echo Checking out to branch '%BRANCH_NAME%'...

:: Check if we're already on this branch
for /f "tokens=*" %%a in ('git rev-parse --abbrev-ref HEAD') do set "CURRENT_BRANCH=%%a"
if "%CURRENT_BRANCH%"=="%BRANCH_NAME%" (
    echo [OK] Already on branch '%BRANCH_NAME%'
    git pull origin %BRANCH_NAME%
) else (
    :: Check if branch exists locally
    git show-ref --verify --quiet refs/heads/%BRANCH_NAME%
    if %errorlevel% equ 0 (
        :: Branch exists locally, just checkout
        git checkout %BRANCH_NAME%
        git pull origin %BRANCH_NAME%
    ) else (
        :: Branch doesn't exist locally, checkout from remote
        git checkout -b %BRANCH_NAME% origin/%BRANCH_NAME%
    )
)

if %errorlevel% neq 0 (
    echo [ERROR] Failed to checkout to branch '%BRANCH_NAME%'
    exit /b 1
)

echo.
echo ============================================================
echo   Outputs Repository Checkout Complete!
echo ============================================================
echo.
echo [OK] You are now on branch '%BRANCH_NAME%' in the Outputs folder
echo.

endlocal
exit /b 0
