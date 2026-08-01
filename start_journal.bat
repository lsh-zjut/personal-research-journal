@echo off
chcp 65001 >nul
cd /d "%~dp0"
call conda activate research-journal
if errorlevel 1 (
  echo 无法激活 research-journal 环境，请先在 Anaconda Prompt 中运行本脚本。
  pause
  exit /b 1
)
echo 正在启动研迹科研日志，请在浏览器访问 http://127.0.0.1:5000
python app.py
pause
