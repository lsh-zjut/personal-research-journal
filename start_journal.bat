@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=D:\conda\Miniconda\envs\research-journal\python.exe"
if not exist "%PYTHON_EXE%" (
  echo The research-journal Python environment was not found.
  echo Create it using the installation command in README.md.
  exit /b 1
)

echo Starting the local Research Journal at http://127.0.0.1:5000
"%PYTHON_EXE%" app.py
endlocal
