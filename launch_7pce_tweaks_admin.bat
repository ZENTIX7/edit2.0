@echo off
setlocal

set SCRIPT_DIR=%~dp0
set APP_SCRIPT=%SCRIPT_DIR%main.py

where py >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py -3
) else (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=python
    ) else (
        echo Python was not found in PATH. Please install Python 3 or add it to PATH.
        pause
        exit /b 1
    )
)

powershell -NoProfile -Command "if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { Start-Process -FilePath 'cmd.exe' -ArgumentList '/c %PYTHON_CMD% \"%APP_SCRIPT%\"' -Verb RunAs } else { Start-Process -FilePath 'cmd.exe' -ArgumentList '/c %PYTHON_CMD% \"%APP_SCRIPT%\"' }"
