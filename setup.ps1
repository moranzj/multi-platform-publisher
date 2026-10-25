[CmdletBinding()]
param(
    [switch]$NoShortcut
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
Set-Location -LiteralPath $root

try {
    [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
    $OutputEncoding = [Text.UTF8Encoding]::new($false)
} catch {
    # 老系统/非控制台环境下编码设置失败不影响安装
}

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok([string]$Message) {
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warn([string]$Message) {
    Write-Host "[!] $Message" -ForegroundColor Yellow
}

function Write-Err([string]$Message) {
    Write-Host "[X] $Message" -ForegroundColor Red
}

function Get-PythonVersion([string]$Exe, [string[]]$PyArgs) {
    try {
        # 注意：Windows PowerShell 5.1 对带空格的原生参数处理不稳，
        # 这里用不含空格的表达式，避免 -c 被截断。
        $versionArgs = @($PyArgs) + @(
            '-c',
            "print('%d.%d'%__import__('sys').version_info[:2])"
        )
        $out = & $Exe @versionArgs 2>$null
        if ($LASTEXITCODE -ne 0) {
            return $null
        }
        return [string]($out | Select-Object -Last 1)
    } catch {
        return $null
    }
}

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  多平台视频发布器 - 一键安装" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "项目目录: $root"

# 1) 找一个可用的 Python 3.9+
$candidates = @(
    @{ Exe = 'py'; Args = @('-3.13') },
    @{ Exe = 'py'; Args = @('-3.12') },
    @{ Exe = 'py'; Args = @('-3.11') },
    @{ Exe = 'py'; Args = @('-3.10') },
    @{ Exe = 'py'; Args = @('-3.9') },
    @{ Exe = 'py'; Args = @('-3') },
    @{ Exe = 'python'; Args = @() },
    @{ Exe = 'python3'; Args = @() }
)

$selected = $null
$selectedVersion = $null
foreach ($candidate in $candidates) {
    if (-not (Get-Command $candidate.Exe -ErrorAction SilentlyContinue)) {
        continue
    }
    $version = Get-PythonVersion $candidate.Exe $candidate.Args
    if (-not $version) {
        continue
    }
    $parts = $version.Split('.')
    if ($parts.Length -lt 2) {
        continue
    }
    $major = 0
    $minor = 0
    [void][int]::TryParse($parts[0], [ref]$major)
    [void][int]::TryParse($parts[1], [ref]$minor)
    if ($major -eq 3 -and $minor -ge 9) {
        $selected = $candidate
        $selectedVersion = $version
        break
    }
}

if (-not $selected) {
    Write-Err "没有找到可用的 Python 3.9+。"
    Write-Host "请先安装 Python 3.11（安装时勾选 Add python.exe to PATH）："
    Write-Host "https://www.python.org/downloads/windows/"
    exit 1
}

$launcher = ((@($selected.Exe) + $selected.Args) -join ' ').Trim()
Write-Ok "找到 Python $selectedVersion（$launcher）"

# 2) 创建独立虚拟环境
$venvDir = Join-Path $root '.venv'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'
$venvPythonw = Join-Path $venvDir 'Scripts\pythonw.exe'

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Step "创建虚拟环境 .venv（不会影响系统 Python）"
    $createArgs = @($selected.Args) + @('-m', 'venv', '.venv')
    & $selected.Exe @createArgs
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $venvPython)) {
        Write-Err "创建虚拟环境失败。"
        exit 1
    }
    Write-Ok "虚拟环境已创建"
} else {
    Write-Step "复用已有的虚拟环境 .venv"
    Write-Ok ".venv 已存在"
}

# 3) 安装依赖
Write-Step "安装 Python 依赖（首次需要联网，可能要几分钟）"
$requirements = Join-Path $root 'requirements.txt'
$env:PIP_DISABLE_PIP_VERSION_CHECK = '1'
$env:PIP_NO_INPUT = '1'
& $venvPython -m pip install -r $requirements --timeout 30 --retries 2
if ($LASTEXITCODE -ne 0) {
    Write-Err "依赖安装失败。请检查网络或代理后重新运行 setup.bat。"
    Write-Host "如果使用代理，可以先在 PowerShell 里设置 HTTP_PROXY / HTTPS_PROXY 再运行。"
    exit 1
}
Write-Ok "依赖安装完成"

# 4) 环境自检
Write-Step "运行环境自检"
$doctorCode = 1
try {
    & $venvPython (Join-Path $root 'cli.py') doctor
    $doctorCode = $LASTEXITCODE
} catch {
    Write-Warn "环境自检执行失败：$($_.Exception.Message)"
}
if ($doctorCode -eq 0) {
    Write-Ok "环境自检通过"
} else {
    Write-Warn "环境自检没有完全通过。依赖已经装好，请按上面的提示修复后再使用。"
}

# 5) 桌面快捷方式
Write-Step "创建桌面快捷方式"
if ($NoShortcut) {
    Write-Host "已跳过（-NoShortcut）"
} else {
    try {
        $desktop = [Environment]::GetFolderPath('Desktop')
        if (-not $desktop) {
            throw '找不到桌面目录'
        }
        if (-not (Test-Path -LiteralPath $venvPythonw)) {
            $venvPythonw = $venvPython
        }
        $shortcutPath = Join-Path $desktop '多平台视频发布器.lnk'
        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = $venvPythonw
        $shortcut.Arguments = '"' + (Join-Path $root 'gui.py') + '"'
        $shortcut.WorkingDirectory = $root
        $shortcut.IconLocation = "$venvPythonw,0"
        $shortcut.Description = '多平台视频发布器'
        $shortcut.Save()
        Write-Ok "桌面快捷方式：$shortcutPath"
    } catch {
        Write-Warn "桌面快捷方式创建失败：$($_.Exception.Message)"
        Write-Host "不影响使用，可以直接双击项目里的 启动.bat。"
    }
}

Write-Host ""
if ($doctorCode -eq 0) {
    Write-Ok "安装完成。"
} else {
    Write-Warn "安装完成，但环境自检有警告，请先处理上面的提示。"
}
Write-Host ""
Write-Host "启动      : 双击桌面「多平台视频发布器」，或项目里的 启动.bat"
Write-Host "首次登录  : 双击 登录.bat，三个平台各扫码一次"
Write-Host "日志      : logs\"
Write-Host "重新安装  : 再次运行 setup.bat 即可"
exit 0
