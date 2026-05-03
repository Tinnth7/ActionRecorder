@echo off
REM ActionRecorder - Build EXE using PyInstaller
REM This script converts the Python application to a standalone .exe file

setlocal enabledelayedexpansion

echo ========================================
echo ActionRecorder EXE Builder
echo ========================================
echo.

REM Activate virtual environment
echo Activating virtual environment...
call .venv-1\Scripts\activate.bat
if errorlevel 1 (
    echo Error: Failed to activate virtual environment
    pause
    exit /b 1
)
echo Virtual environment activated
echo.

REM Check if PyInstaller is installed
echo Checking for PyInstaller...
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo Error: Failed to install PyInstaller
        pause
        exit /b 1
    )
) else (
    echo PyInstaller is already installed
)
echo.

REM Build the executable
echo Building executable...
echo This may take a minute or two...
echo.

pyinstaller --onefile --windowed --name ActionRecorder ^
    --icon=icon.ico ^
    main.py

if errorlevel 1 (
    echo.
    echo Error: Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo The executable is located at:
echo   dist\ActionRecorder.exe
echo.
pause
