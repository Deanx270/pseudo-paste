@echo off
echo ==============================================
echo Building Pseudo Paste Standalone Executable (.exe)
echo ==============================================

echo Checking PyInstaller...
python -m pip install pyinstaller

echo Packaging application...
python -m PyInstaller --noconsole --onefile --collect-all customtkinter --name PseudoPaste pseudo_paste.py

echo.
echo Build complete! You can find PseudoPaste.exe in the 'dist' folder.
pause
