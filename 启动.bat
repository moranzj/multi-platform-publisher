@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

"%PY%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
if errorlevel 1 (
    echo [错误] 没有找到可用的 Python 3.9+，或 .venv 已损坏。
    echo        请先双击 setup.bat 一键安装。
    pause
    exit /b 1
)

"%PY%" -c "import playwright" >nul 2>nul
if errorlevel 1 (
    echo [错误] 缺少 Playwright 依赖。请先双击 setup.bat，或运行：
    echo     pip install -r requirements.txt
    pause
    exit /b 1
)

set "PYW=pythonw"
if exist ".venv\Scripts\pythonw.exe" set "PYW=.venv\Scripts\pythonw.exe"

"%PYW%" -c "import sys" >nul 2>nul
if errorlevel 1 (
    "%PY%" "gui.py"
) else (
    start "" "%PYW%" "gui.py"
)
