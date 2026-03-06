@echo off
echo ========================================
echo Building OBD Diagnostics .exe
echo ========================================
echo.

echo [1/3] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install requirements
    pause
    exit /b 1
)

echo.
echo [2/3] Building executable with PyInstaller...
pyinstaller --onefile --windowed --name "OBD_Diagnostics" --noconsole main.py
if errorlevel 1 (
    echo ERROR: PyInstaller failed
    pause
    exit /b 1
)

echo.
echo [3/3] Done!
echo.
echo Executable created: dist\OBD_Diagnostics.exe
echo.
pause
