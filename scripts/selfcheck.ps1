<#
.SYNOPSIS
    Самопроверка AI Team System одной командой.

.DESCRIPTION
    Поднимает приложение на отдельном порту, проверяет всё по порядку и убирает за собой:
      1. приложение отвечает;
      2. модель отвечает изнутри приложения (главная причина «модель не ответила»);
      3. список проектов читается;
      4. список провайдеров отдаётся;
      5. очередь подтверждений доступна.

    Ничего не пишет в проект и не мешает запущенному приложению: порт свой, процесс свой.

.EXAMPLE
    pwsh scripts\selfcheck.ps1
    pwsh scripts\selfcheck.ps1 -Port 8020
#>
param(
    [int]$Port = 8011
)

try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
try { chcp 65001 > $null } catch { }

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = 'python' }

$env:USERPROFILE = $env:USERPROFILE
$server = $null
$failures = 0

function Step($name, [scriptblock]$check) {
    try {
        $result = & $check
        if ($result) {
            Write-Host ("  OK   " + $name) -ForegroundColor Green
        } else {
            Write-Host ("  СБОЙ " + $name) -ForegroundColor Red
            $script:failures++
        }
    } catch {
        Write-Host ("  СБОЙ " + $name + ": " + $_.Exception.Message) -ForegroundColor Red
        $script:failures++
    }
}

try {
    # Свой порт: чужое приложение не мешает, и наоборот.
    $busy = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    if ($busy) { throw "Порт $Port занят. Запусти с другим портом: pwsh scripts\selfcheck.ps1 -Port 8020" }

    Write-Host "Поднимаю приложение на порту $Port ..."
    $server = Start-Process -FilePath $python `
        -ArgumentList @('-m', 'uvicorn', 'web_ui.app:app', '--host', '127.0.0.1', '--port', "$Port") `
        -WorkingDirectory $root -PassThru -WindowStyle Hidden

    $base = "http://127.0.0.1:$Port"
    $up = $false
    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 500
        try { if ((Invoke-WebRequest "$base/" -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200) { $up = $true; break } } catch { }
    }
    if (-not $up) { throw "Приложение не поднялось за 20 секунд" }

    Write-Host "Проверки:"
    Step "страница приложения" { (Invoke-WebRequest "$base/" -UseBasicParsing -TimeoutSec 10).StatusCode -eq 200 }
    Step "модель отвечает изнутри приложения" {
        $r = Invoke-RestMethod "$base/api/health/model" -TimeoutSec 240
        if ($r.ok) { $true } else { Write-Host ("       причина: " + ($r.error + $r.answer)) -ForegroundColor DarkYellow; $false }
    }
    Step "список проектов" { (Invoke-RestMethod "$base/api/sessions" -TimeoutSec 20).sessions -ne $null }
    Step "каталог провайдеров" { (Invoke-RestMethod "$base/api/providers" -TimeoutSec 20).providers.Count -gt 0 }
    Step "очередь подтверждений" { $null -ne (Invoke-RestMethod "$base/api/developer/approvals" -TimeoutSec 20).count }

    Write-Host ""
    if ($failures -eq 0) {
        Write-Host "ИТОГ: всё живо." -ForegroundColor Green
    } else {
        Write-Host "ИТОГ: сбоев — $failures. Выше видно, где именно." -ForegroundColor Yellow
    }
} finally {
    if ($server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
        Write-Host "Проверочный сервер остановлен."
    }
}

exit $failures
