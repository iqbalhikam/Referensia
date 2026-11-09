@echo off
rem ============================================================
rem  Bungkus server Python Referensia jadi sidecar .exe untuk Tauri
rem  Jalankan SEKALI sebelum: npx tauri build --bundles nsis
rem ============================================================
cd /d %~dp0..\backend

call .venv\Scripts\python -m pip install -q pyinstaller
if errorlevel 1 exit /b 1

call .venv\Scripts\pyinstaller --noconfirm --onefile --name referensia-server --collect-submodules sklearn --collect-all docx --collect-all openpyxl server.py
if errorlevel 1 exit /b 1

if not exist ..\src-tauri\binaries mkdir ..\src-tauri\binaries
copy /y dist\referensia-server.exe ..\src-tauri\binaries\referensia-server-x86_64-pc-windows-msvc.exe
if errorlevel 1 exit /b 1

echo.
echo SELESAI — sidecar siap di src-tauri\binaries\
echo Selanjutnya: cd app ^&^& npx tauri build --bundles nsis