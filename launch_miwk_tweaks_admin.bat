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

%PYTHON_CMD% -m pip show PySide6 >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing requirements...
    %PYTHON_CMD% -m pip install -r "%SCRIPT_DIR%requirements.txt"
    if %errorlevel% neq 0 (
        echo Failed to install requirements. Please run: %PYTHON_CMD% -m pip install -r "%SCRIPT_DIR%requirements.txt"
        pause
        exit /b 1
    )
)

powershell -NoProfile -Command "if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { Start-Process -FilePath 'cmd.exe' -ArgumentList '/c %PYTHON_CMD% \"%APP_SCRIPT%\" > \"%SCRIPT_DIR%launch_stdout.log\" 2> \"%SCRIPT_DIR%launch_stderr.log\"' -Verb RunAs } else { Start-Process -FilePath 'cmd.exe' -ArgumentList '/c %PYTHON_CMD% \"%APP_SCRIPT%\" > \"%SCRIPT_DIR%launch_stdout.log\" 2> \"%SCRIPT_DIR%launch_stderr.log\"' }"
