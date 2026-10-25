@echo off
chcp 65001 >nul
cd /d "%~dp0"

where powershell >nul 2>nul
if errorlevel 1 (
    echo [错误] 找不到 PowerShell，无法继续安装。
    echo        请确认系统是 Windows 10/11，或手动运行：
    echo        pip install -r requirements.txt
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
    echo [失败] 安装没有完成，请查看上面的错误信息。
) else (
    echo [完成] 安装结束。
)
echo.
pause
exit /b %RC%
