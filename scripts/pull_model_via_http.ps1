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

# Скачивание идёт через System.Net.Http пофрагментно: клиент Ollama и curl
# на части сетей получают обрыв соединения, а короткие Range-запросы проходят.
function Save-BlobChunked {
    param(
        [string]$Url,
        [string]$Target,
        [int64]$Expected,
        [int]$ChunkMB = 8,
        [int]$MaxRetries = 6
    )

    $client = [System.Net.Http.HttpClient]::new()
    $client.Timeout = [TimeSpan]::FromMinutes(5)

    if (-not (Test-Path $Target)) { New-Item -ItemType File -Path $Target -Force | Out-Null }

    $chunk = [int64]$ChunkMB * 1MB
    $offset = (Get-Item $Target).Length
    $failures = 0
    $lastReport = 0

    while ($offset -lt $Expected) {
        $end = [Math]::Min($offset + $chunk - 1, $Expected - 1)
        try {
            $req = [System.Net.Http.HttpRequestMessage]::new([System.Net.Http.HttpMethod]::Get, $Url)
            $req.Headers.Range = [System.Net.Http.Headers.RangeHeaderValue]::new($offset, $end)
            $resp = $client.Send($req)
            if (-not $resp.IsSuccessStatusCode) { throw "HTTP $([int]$resp.StatusCode)" }

            $bytes = $resp.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
            if ($bytes.Length -eq 0) { throw "пустой ответ" }

            $fs = [System.IO.File]::Open($Target, [System.IO.FileMode]::Append, [System.IO.FileAccess]::Write)
            try { $fs.Write($bytes, 0, $bytes.Length) } finally { $fs.Dispose() }

            $offset += $bytes.Length
            $failures = 0
            if (($offset - $lastReport) -ge 250MB) {
                $lastReport = $offset
                Write-Output ("   {0:N2} / {1:N2} GB" -f ($offset / 1GB), ($Expected / 1GB))
            }
        }
        catch {
            $failures++
            if ($failures -ge $MaxRetries) {
                $client.Dispose()
                throw "Не удалось скачать $Url после $MaxRetries попыток. Запусти скрипт ещё раз — докачка продолжится."
            }
            Start-Sleep -Seconds 2
            $offset = if (Test-Path $Target) { (Get-Item $Target).Length } else { 0 }
        }
    }

    $client.Dispose()
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

    Save-BlobChunked -Url $url -Target $target -Expected $expected -MaxRetries $MaxRetries

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
