<#
.SYNOPSIS
    Запуск AI Team System на Windows одной командой.

.DESCRIPTION
    Скрипт делает всё, что нужно для старта:
      1. находит Python 3.10+ и создаёт виртуальное окружение .venv;
      2. ставит зависимости из requirements.txt (если их ещё нет);
      3. создаёт .env из .env.example при первом запуске;
      4. поднимает Ollama, если она установлена, но не запущена;
      5. стартует веб-сервер и открывает браузер на http://localhost:8000.

.PARAMETER Port
    Порт веб-сервера (по умолчанию 8000).

.PARAMETER NoBrowser
    Не открывать браузер автоматически.

.EXAMPLE
    pwsh scripts/launcher.ps1
#>
[CmdletBinding()]
param(
    [int]$Port = 8000,
    [switch]$NoBrowser
)

# Русский текст в консоли Windows: без этого сообщения выводятся кракозябрами,
# и человек не может прочитать, что именно сломалось.
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
try { chcp 65001 > $null } catch { }
$OutputEncoding = [System.Text.Encoding]::UTF8

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

# ── 1. Python ────────────────────────────────────────────────────────────────
$py = $null
$candidates = @(
    (Join-Path $env:USERPROFILE "AppData\Local\Programs\Python\Python313\python.exe"),
    (Join-Path $env:USERPROFILE "AppData\Local\Programs\Python\Python312\python.exe"),
    (Join-Path $env:USERPROFILE "AppData\Local\Programs\Python\Python311\python.exe")
)
foreach ($c in $candidates) {
    if (Test-Path $c) { $py = $c; break }
}
if (-not $py) {
    $found = Get-Command python -ErrorAction SilentlyContinue
    if ($found -and $found.Source -notlike "*WindowsApps*") { $py = $found.Source }
}
if (-not $py) {
    throw "Python не найден. Установи его: winget install Python.Python.3.13 — и запусти скрипт снова."
}
Write-Output "Python: $py"

# ── 2. Виртуальное окружение ─────────────────────────────────────────────────
$venv = Join-Path $root ".venv"
$venvPy = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Output "Создаю виртуальное окружение .venv ..."
    & $py -m venv $venv
}
if (-not (Test-Path $venvPy)) { throw "Не удалось создать venv в $venv" }

# ── 3. Зависимости ───────────────────────────────────────────────────────────
& $venvPy -c "import fastapi" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Output "Устанавливаю зависимости (первый запуск, это займёт минуту) ..."
    # PIP_USER и PYTHONUSERBASE ломают установку внутрь venv, если скрипт
    # запускается из окружения агента — на время установки их гасим.
    Remove-Item Env:PIP_USER -ErrorAction SilentlyContinue
    Remove-Item Env:PYTHONUSERBASE -ErrorAction SilentlyContinue
    & $venvPy -m pip install --upgrade pip
    & $venvPy -m pip install -r (Join-Path $root "requirements.txt")
}

# ── 4. .env ──────────────────────────────────────────────────────────────────
$envFile = Join-Path $root ".env"
$envSample = Join-Path $root ".env.example"
if (-not (Test-Path $envFile) -and (Test-Path $envSample)) {
    Copy-Item $envSample $envFile
    Write-Output "Создан .env из .env.example (ключи можно вписать позже)"
}

# ── 5. Ollama ────────────────────────────────────────────────────────────────
$ollamaUp = $false
try {
    Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 | Out-Null
    $ollamaUp = $true
} catch { $ollamaUp = $false }

if (-not $ollamaUp) {
    $ollamaApp = Join-Path $env:USERPROFILE "AppData\Local\Programs\Ollama\ollama app.exe"
    if (Test-Path $ollamaApp) {
        Write-Output "Поднимаю Ollama ..."
        Start-Process -FilePath $ollamaApp | Out-Null
        for ($i = 0; $i -lt 20; $i++) {
            Start-Sleep -Seconds 1
            try {
                Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 | Out-Null
                $ollamaUp = $true; break
            } catch { }
        }
    }
}
if ($ollamaUp) {
    $tags = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 5
    $names = @($tags.models | ForEach-Object { $_.name })
    if ($names.Count -eq 0) {
        Write-Output "Ollama запущена, но моделей нет. Поставь модель:"
        Write-Output "  ollama pull qwen3:8b"
        Write-Output "  или, если сеть рвёт загрузку: pwsh scripts/pull_model_via_http.ps1 -Model qwen3 -Tag 8b"
    } else {
        Write-Output ("Ollama: " + ($names -join ", "))
    }
} else {
    Write-Output "Ollama недоступна — чат с агентами не ответит, но интерфейс запустится."
    Write-Output "Установить: winget install Ollama.Ollama"
}

# ── 6. Освобождаем порт: старый сервер закрываем сами ────────────────────────
# Лаунчер не должен спихивать это на человека: он сам находит занявший порт процесс.
# Закрываем только Python (сервер проекта). Чужие программы не трогаем —
# вместо этого говорим прямо, кто мешает.
$busy = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
if ($busy) {
    $oldPid = $busy.OwningProcess
    $oldProc = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
    if ($oldProc -and $oldProc.ProcessName -match '^(python|pythonw|uvicorn)') {
        Write-Output "Порт $Port занят прошлым сервером (PID $oldPid) — закрываю его."
        try {
            Stop-Process -Id $oldPid -Force -ErrorAction Stop
            for ($i = 0; $i -lt 10; $i++) {
                Start-Sleep -Milliseconds 300
                if (-not (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)) { break }
            }
        } catch {
            throw "Не удалось закрыть прошлый сервер (PID $oldPid). Закрой его вручную и запусти снова."
        }
        Write-Output "Порт $Port освобождён."
    } else {
        $who = if ($oldProc) { $oldProc.ProcessName } else { 'неизвестная программа' }
        throw "Порт $Port занят: $who (PID $oldPid). Это не сервер проекта — закрой её или укажи другой порт: pwsh scripts/launcher.ps1 -Port 8010"
    }
}

# ── 7. Старт сервера ─────────────────────────────────────────────────────────
Write-Output "Запускаю сервер на http://localhost:$Port ..."
$proc = Start-Process -FilePath $venvPy `
    -ArgumentList @("-m", "uvicorn", "web_ui.app:app", "--host", "127.0.0.1", "--port", "$Port") `
    -WorkingDirectory $root -PassThru -WindowStyle Minimized

$url = "http://localhost:$Port"
$ok = $false
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 750
    try {
        $h = Invoke-RestMethod -Uri "$url/api/health" -TimeoutSec 3
        if ($h.status -eq "ok") { $ok = $true; break }
    } catch { }
}

if (-not $ok) {
    Write-Output "Сервер не ответил за 30 секунд. Проверь журнал в окне сервера."
    Write-Output "PID процесса: $($proc.Id)"
    exit 1
}

Write-Output "Готово. Интерфейс: $url"
if (-not $NoBrowser) { Start-Process $url | Out-Null }

Write-Output ""
Write-Output "Как остановить сервер: Stop-Process -Id $($proc.Id)"
Write-Output "Либо закройте свёрнутое окно сервера."
