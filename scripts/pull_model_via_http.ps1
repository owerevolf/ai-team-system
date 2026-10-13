<#
.SYNOPSIS
    Ставит модель Ollama напрямую по HTTP, если `ollama pull` рвёт соединение.

.DESCRIPTION
    На части сетей (в частности в РФ) клиент Ollama получает
    "An existing connection was forcibly closed by the remote host" при
    обращении к registry.ollama.ai, хотя сам реестр доступен и отдаёт файлы:
    обычный HTTP-запрос скачивает те же данные без обрывов.

    Скрипт берёт манифест модели, скачивает конфиг и все слои через curl
    с докачкой и раскладывает их в локальное хранилище Ollama. После этого
    `ollama list` и приложение видят модель как обычно установленную.

.PARAMETER Model
    Имя модели в реестре (например qwen3).

.PARAMETER Tag
    Тег модели (например 8b).

.PARAMETER MaxRetries
    Сколько раз перезапускать докачку одного файла.

.EXAMPLE
    pwsh scripts/pull_model_via_http.ps1 -Model qwen3 -Tag 8b
#>
[CmdletBinding()]
param(
    [string]$Model = "qwen3",
    [string]$Tag = "8b",
    [int]$MaxRetries = 8
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) {
    throw "Нужен curl.exe (входит в Windows 10/11). Установи curl или используй обычный ollama pull."
}

$registry = "https://registry.ollama.ai/v2/library"
$storeRoot = Join-Path $env:USERPROFILE ".ollama\models"
$blobsDir = Join-Path $storeRoot "blobs"
$manifestDir = Join-Path $storeRoot "manifests\registry.ollama.ai\library\$Model"
$manifestFile = Join-Path $manifestDir $Tag

New-Item -ItemType Directory -Force -Path $blobsDir, $manifestDir | Out-Null

Write-Output "1. Манифест $Model`:$Tag"
$manifestUrl = "$registry/$Model/manifests/$Tag"
$webResp = Invoke-WebRequest -Uri $manifestUrl `
    -Headers @{ Accept = "application/vnd.docker.distribution.manifest.v2+json" } `
    -TimeoutSec 60

# Invoke-WebRequest отдаёт Content как byte[], если тип ответа не текстовый
$manifestJson = if ($webResp.Content -is [byte[]]) {
    [System.Text.Encoding]::UTF8.GetString($webResp.Content)
}
else {
    [string]$webResp.Content
}
if ([string]::IsNullOrWhiteSpace($manifestJson)) {
    throw "Реестр вернул пустой манифест для $Model`:$Tag"
}

$manifest = $manifestJson | ConvertFrom-Json
if (-not $manifest -or -not $manifest.layers) {
    throw "Не удалось разобрать манифест $Model`:$Tag"
}
Set-Content -Path $manifestFile -Value $manifestJson -NoNewline -Encoding utf8

# 2. Конфиг + все слои
$items = @()
if ($manifest.config) { $items += $manifest.config }
$items += @($manifest.layers | Where-Object { $_ })

foreach ($item in $items) {
    $digest = $item.digest
    if (-not $digest -or $digest -notlike "*:*") { continue }
    $hex = $digest.Split(":")[1]
    $target = Join-Path $blobsDir "sha256-$hex"
    $expected = [int64]$item.size

    if ((Test-Path $target) -and ((Get-Item $target).Length -eq $expected)) {
        Write-Output ("   уже на месте: sha256-{0}... ({1:N2} GB)" -f $hex.Substring(0, 12), ($expected / 1GB))
        continue
    }

    $url = "$registry/$Model/blobs/$digest"
    Write-Output ("2. Качаю sha256-{0}... ({1:N2} GB)" -f $hex.Substring(0, 12), ($expected / 1GB))

    for ($i = 1; $i -le $MaxRetries; $i++) {
        # -C - продолжает файл с текущего размера, --retry-* повторяет обрывы
        & curl.exe -L --http1.1 -sS --retry 3 --retry-delay 2 --retry-all-errors `
            -C - -o "$target" "$url" 2>&1 | Out-Null

        $size = if (Test-Path $target) { (Get-Item $target).Length } else { 0 }
        if ($size -eq $expected) { break }
        Write-Output ("   попытка {0}: {1:N2} / {2:N2} GB" -f $i, ($size / 1GB), ($expected / 1GB))
        Start-Sleep -Seconds 3
    }

    $size = if (Test-Path $target) { (Get-Item $target).Length } else { 0 }
    if ($size -ne $expected) {
        throw "Не удалось скачать $digest ($size из $expected байт). Запусти скрипт ещё раз — докачка продолжится."
    }
    Write-Output "   готово"
}

Write-Output ""
Write-Output "Модель установлена. Проверка:"

$ollamaExe = (Get-Command ollama -ErrorAction SilentlyContinue).Source
if (-not $ollamaExe) {
    $ollamaExe = Join-Path $env:USERPROFILE "AppData\Local\Programs\Ollama\ollama.exe"
}
if (Test-Path $ollamaExe) { & $ollamaExe list } else { Write-Output "Запусти: ollama list" }
