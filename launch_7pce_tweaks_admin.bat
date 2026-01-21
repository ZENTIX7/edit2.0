@echo off
setlocal

set SCRIPT_DIR=%~dp0
set APP_SCRIPT=%SCRIPT_DIR%main.py

powershell -NoProfile -Command "if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { Start-Process -FilePath 'python' -ArgumentList '\"%APP_SCRIPT%\"' -Verb RunAs } else { Start-Process -FilePath 'python' -ArgumentList '\"%APP_SCRIPT%\"' }"
