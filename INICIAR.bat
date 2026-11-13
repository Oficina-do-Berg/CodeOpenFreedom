@echo off
title CodeOpen - by OFICINA-DO-BERG
cd /d "%~dp0"
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe select_language.py
) else (
    python select_language.py
)
pause
