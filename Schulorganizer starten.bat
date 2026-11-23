@echo off
cd /d "%~dp0programm"
where pyw >nul 2>nul && (start "" pyw schulorganizer.py & exit /b)
where pythonw >nul 2>nul && (start "" pythonw schulorganizer.py & exit /b)
echo Python wurde nicht gefunden. Bitte zuerst Python installieren (python.org/downloads, Haken bei "Add python.exe to PATH" setzen).
start https://www.python.org/downloads/
pause
