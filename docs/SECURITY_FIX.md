# Правка безопасности, которую должен внести владелец

**Зачем этот файл:** аудит 14.10.2026 нашёл, что локальный сервер был доступен для
постороннего кода. Часть дыр уже закрыта в коде (см. «Что уже сделано»), но
`web_ui/app.py` агент записать не может — файл блокирует фильтр записи, потому что
в нём есть строки с `api_key`. Правку нужно внести руками: она маленькая и точная.

---

## Что уже сделано (в репозитории)

1. `core/project_manager/runtime/developer/developer_terminal.py`
   - запрещены цепочки и перенаправления (`;`, `&&`, `||`, `|`, `&`, backtick, `$(`, `${`, `>`, `<`, `^`, перенос строки);
   - запрещены опасные аргументы: `python -c`, `python -i`, `git push`, `git config`,
     `git remote set-url`, `git branch -D`, `find -delete/-exec`, `pip install`,
     `npm/yarn install|add|exec|create`, `npx`;
   - убран ложный запрет на `cat <файл>` (он срабатывал из-за подстроки `"at "`).
2. `core/project_manager/runtime/developer/developer_api.py`
   - роуты `POST /api/developer/terminal` и `POST /api/developer/execute` теперь выключены
     по умолчанию и отдают `403`. Включаются явно: `AITEAM_DEV_EXEC=1` в `.env`.
3. `.env.example` — добавлены `AITEAM_DEV_EXEC`, `AITEAM_HOST`, `AITEAM_ALLOWED_ORIGINS`.
4. `tests/test_security_hardening.py` — тесты на цепи, опасные аргументы и закрытые роуты.

---

## Правка №1 — CORS (файл `web_ui/app.py`)

**Найди:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Замени на:**
```python
# CORS: только локальные адреса. Раньше стояло ["*"] вместе с credentials —
# это позволяло любой открытой в браузере странице отправлять запросы на локальный сервер.
_allowed_origins = [
    o.strip() for o in os.getenv(
        "AITEAM_ALLOWED_ORIGINS",
        "http://127.0.0.1:8000,http://localhost:8000",
    ).split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Правка №2 — адрес прослушивания (в конце того же файла)

**Найди:**
```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_ui.app:app", host="0.0.0.0", port=8000, reload=False)
```

**Замени на:**
```python
if __name__ == "__main__":
    import uvicorn
    # По умолчанию слушаем только локальный интерфейс: выход в сеть приложению не нужен.
    # Нужен доступ с других устройств — задай AITEAM_HOST=0.0.0.0 осознанно.
    uvicorn.run("web_ui.app:app", host=os.getenv("AITEAM_HOST", "127.0.0.1"), port=8000, reload=False)
```

---

## После правки

1. Проверить, что тест CORS стал зелёным, и **снять маркер** `xfail` с
   `tests/test_security_hardening.py::TestCorsIsLocalOnly::test_cors_origins_are_local`
   (маркер специально `strict`: пока он стоит, зелёный тест даёт ошибку).
2. Прогнать полный набор:
   `python -m pytest tests -q --ignore=tests/test_integration.py`
3. Коммит: `pwsh scripts/agent_commit.ps1 -Message "fix: harden CORS and bind address" -Push`

---

## Почему это важно

Роут терминала не требовал ни авторизации, ни подтверждения, а валидатор пропускал
цепочки команд. При CORS `*` и сервере на `0.0.0.0` этого хватало, чтобы любая открытая
страница или программа в локальной сети выполнила произвольную команду на этой машине.
Теперь терминал закрыт флагом, а последний шаг — ограничить CORS и адрес прослушивания.
