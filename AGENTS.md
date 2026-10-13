# AGENTS.md — правила работы агентов в этом репозитории

## Коммиты

Автор и коммиттер любого коммита — **владелец репозитория** (значения
`user.name` / `user.email` из git config). Вклад агента фиксируется трейлером
`Co-authored-by` — GitHub показывает его как соавтора.

Агентские платформы подставляют в окружение `GIT_AUTHOR_NAME/EMAIL` и
`GIT_COMMITTER_NAME/EMAIL` (например `zwork <zwork@local>`). Эти переменные
перекрывают git config, поэтому коммит «уезжает» на служебное имя. Коммитить
нужно через обёртку, она возвращает авторство владельцу:

```powershell
pwsh scripts/agent_commit.ps1 -Message "fix: ..." -Body "детали правки"
pwsh scripts/agent_commit.ps1 -Message "..." -NoAdd -Amend   # переоформить последний коммит
pwsh scripts/agent_commit.ps1 -Message "..." -Push           # коммит и push
```

Перед первым коммитом в новом клоне проверь, что владелец задан:

```powershell
git config user.name; git config user.email
```

## Проверки перед коммитом

```powershell
python -m pytest tests -q --ignore=tests/test_integration.py
```

Один тест падает на Windows по платформенной причине:
`test_install.py::TestInstallScript::test_install_sh_executable` — у `install.sh`
нет exec-бита в файловой системе Windows. В CI на Linux он проходит, это
не регрессия. Не «чинить» его удалением или ослаблением проверки.

## Провайдеры моделей

- Локально: Ollama (`OLLAMA_BASE_URL`, `OLLAMA_MODEL`), режим `AI_MODE=local`.
- Любой OpenAI-совместимый эндпоинт: `OPENAI_COMPAT_BASE_URL`,
  `OPENAI_COMPAT_API_KEY`, `OPENAI_COMPAT_MODEL` (провайдер `openai_compat`).
- OpenRouter с 27.06.2026 не обслуживает российские аккаунты и IP — ключ
  имеет смысл только за пределами РФ.

## Гигиена репозитория

Не коммитить `venv*/`, `.cache/`, `*.log`, `.env` — они перечислены в
`.gitignore`. Ключи и токены живут только в `.env` (в репозиторий не попадают).
