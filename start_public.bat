@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=D:\conda\Miniconda\envs\research-journal\python.exe"
if not exist "%PYTHON_EXE%" (
  echo The research-journal Python environment was not found.
  echo Create it using the installation command in README.md.
  exit /b 1
)

set "JOURNAL_COOKIE_SECURE=1"
set "JOURNAL_BEHIND_PROXY=1"
set "JOURNAL_TRUSTED_HOSTS=zjut-lsh.cn,www.zjut-lsh.cn,localhost,127.0.0.1"

echo Starting the public Research Journal backend at http://127.0.0.1:8000
"%PYTHON_EXE%" -m waitress --listen=127.0.0.1:8000 --threads=4 app:app
endlocal
