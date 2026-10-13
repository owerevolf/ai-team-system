<#
.SYNOPSIS
    Коммит от имени владельца репозитория с пометкой вклада агента.

.DESCRIPTION
    Платформа, из которой запускаются агенты, подставляет переменные окружения
    GIT_AUTHOR_NAME/EMAIL и GIT_COMMITTER_NAME/EMAIL (zwork <zwork@local>).
    Переменные перекрывают git config, поэтому коммит уходит на служебное имя.
    Скрипт берёт владельца из git config, возвращает переменные на него и
    добавляет трейлер Co-authored-by с агентом — GitHub покажет его соавтором.

.PARAMETER Message
    Заголовок коммита (subject).

.PARAMETER Body
    Тело коммита (опционально).

.PARAMETER Agent
    Кто указан соавтором. По умолчанию агент и модель, на которой он исполняется.

.PARAMETER NoAdd
    Не делать git add -A (закоммитить только уже проиндексированное).

.PARAMETER Amend
    Переоформить последний коммит (используется для починки авторства).

.PARAMETER Push
    Сделать git push после коммита.

.EXAMPLE
    pwsh scripts/agent_commit.ps1 -Message "fix: rollback patch" -Body "детали правки"

.EXAMPLE
    pwsh scripts/agent_commit.ps1 -Message "fix: right author" -NoAdd -Amend
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Message,
    [string]$Body = "",
    [string]$Agent = "AutoClaw (zai_auto) <autoclaw@local>",
    [switch]$NoAdd,
    [switch]$Amend,
    [switch]$Push
)

$ErrorActionPreference = "Stop"

# 1. Владелец берётся из git config, а не из окружения — иначе получим zwork
$ownerName = (git config user.name).Trim()
$ownerEmail = (git config user.email).Trim()
if (-not $ownerName -or -not $ownerEmail) {
    throw "Не задан user.name/user.email. Выполни: git config user.name `"Имя`" и git config user.email `"адрес`""
}

# 2. Возвращаем авторство владельцу
$env:GIT_AUTHOR_NAME = $ownerName
$env:GIT_AUTHOR_EMAIL = $ownerEmail
$env:GIT_COMMITTER_NAME = $ownerName
$env:GIT_COMMITTER_EMAIL = $ownerEmail

# 3. Индекс
if (-not $NoAdd) {
    git add -A
}

# 4. Коммит с трейлером соавторства
$gitArgs = @()
if ($Amend) { $gitArgs += "--amend" }
$gitArgs += @("-m", $Message)
if ($Body) { $gitArgs += @("-m", $Body) }
$gitArgs += @("-m", "Co-authored-by: $Agent")

git commit @gitArgs
if ($LASTEXITCODE -ne 0) { throw "git commit завершился с кодом $LASTEXITCODE" }

# 5. Push (если попросили)
if ($Push) {
    git push
    if ($LASTEXITCODE -ne 0) { throw "git push завершился с кодом $LASTEXITCODE" }
}

# 6. Показываем, что получилось
git --no-pager log -1 --pretty=format:"%h%nauthor:    %an <%ae>%ncommitter: %cn <%ce>%n%n%B"
Write-Output ""
