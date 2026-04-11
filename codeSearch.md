# 🔍 ПОЛНЫЙ РАЗБОР ПРОБЛЕМ AI TEAM SYSTEM v2.0

**Дата:** 2026-04-11
**Версия:** 2.0 (FastAPI + Ollama + Docker)

---

## ПРОБЛЕМА #1 — КРИТИЧЕСКАЯ: Второе сообщение пользователя игнорируется

### СИМПТОМ
Пользователь: "дневник поливки цветов" → TeamLead отвечает
Пользователь: "да именно так, какой цветок и как полили..." → **НИЧЕГО НЕ ПРОИСХОДИТ**

### КОРЕНЬ
Файл: `web_ui/templates/welcome.html`, функция `sendMessage()` (строка ~683)

Логика:
```javascript
if (state.phase === 'idea') { ... отправляет в API ... }
else if (state.phase === 'teamlead_questions') { ... отправляет вопрос ... }
else if (state.phase === 'clarify') { ... начинает сборку ... }
else if (state.phase === 'done') { ... новый проект ... }
// ELSE — НИЧЕГО НЕ ДЕЛАЕТ
```

После первого ответа TeamLead, `state.phase` устанавливается в `'teamlead_wait'`.
Когда пользователь отправляет второй ответ — фаза `'teamlead_wait'` **НЕ ОБРАБАТЫВАЕТСЯ**.
Сообщение теряется, API не вызывается.

### РЕШЕНИЕ
Добавить ветку `else if (state.phase === 'teamlead_wait')` в `sendMessage()`:
```javascript
else if (state.phase === 'teamlead_wait') {
  state.projectIdea += `\n\nОтвет пользователя: ${text}`;
  await callTeamLead();
}
```

---

## ПРОБЛЕМА #2 — Стиль ответов: "быдловатость"

### СИМПТОМ
TeamLead отвечает шаблонно, с натянутым юмором ("с зажатым кулаком", "Здарова").

### КОРЕНЬ
Файл: `prompts/roles/teamlead_zero.md` — сленг был слишком агрессивный.

### СТАТУС
✅ **ИСПРАВЛЕНО** — обновлён стиль: интеллигентный, живой, без крайностей.

---

## ПРОБЛЕМА #3 — Docker не видел GPU

### СИМПТОМ
VRAM = 0.0 GB, использовалась модель qwen3:4b вместо qwen3:8b.

### КОРЕНЬ
В docker-compose.yml не было `runtime: nvidia` и `deploy.resources.reservations.devices`.

### СТАТУС
✅ **ИСПРАВЛЕНО** — GPU проброшен, VRAM = 8.0 GB, модель qwen3:8b.

---

## ПРОБЛЕМА #4 — Docker не мог достучаться до Ollama

### СИМПТОМ
"Локальная модель не справилась с задачей" в логах.

### КОРЕНЬ
На Linux `host.docker.internal` не работает без `extra_hosts`, а фаервол блокирует docker0→host.

### СТАТУС
✅ **ИСПРАВЛЕНО** — используется `network_mode: host` + Ollama слушает 0.0.0.0:11434.

---

## ПРОБЛЕМА #5 — Jinja2 ошибка "unhashable type: dict"

### СИМПТОМ
"Internal Server Error" на главной странице.

### КОРЕНЬ
Несовместимость fastapi 0.135.3 + starlette 1.0.0 + jinja2.

### СТАТУС
✅ **ИСПРАВЛЕНО** — pinned fastapi==0.115.6, starlette==0.41.3.

---

## ЧТО РАБОТАЕТ

| Компонент | Статус |
|-----------|--------|
| FastAPI сервер | ✅ Порт 8000, health check OK |
| Docker + GPU | ✅ VRAM 8GB, nvidia runtime |
| Ollama доступ | ✅ 5 моделей, localhost:11434 |
| GitHub Models Vision | ✅ GPT-4o анализ скриншотов |
| Auto-tester v2.0 | ✅ Playwright + Vision + hearing check |
| TeamLead стиль | ✅ Живой, не NPC, не быдло |
| Промпты | ✅ 9 файлов, реагируют на конкретику |

---

## ЧТО СЛОМАНО (ТРЕБУЕТ ИСПРАВЛЕНИЯ)

### КРИТИЧЕСКОЕ:
1. **sendMessage() не обрабатывает state.phase = 'teamlead_wait'** — пользователь не может продолжить диалог
2. **Нет кнопки "Ответить" после ответа TeamLead** — UI показывает только "❓ Есть вопросы" и "✅ Делаем!"

### СРЕДНЕЕ:
3. **welcome.html: 1314 строк** — огромный inline файл, сложно поддерживать
4. **Нет обработки ошибок SSE stream** — если Ollama завис, пользователь не понимает что происходит
5. **Нет индикатора загрузки** — между отправкой и ответом 10-20 секунд тишины

### НИЗКОЕ:
6. **Healthcheck в Docker** — `/health` вместо `/api/health` (404 в логах)
7. **`.env` в контейнере копируется из `.env.example`** — реальные ключи не подхватываются

---

## ПРИОРИТЕТ ИСПРАВЛЕНИЯ

1. `sendMessage()` + `teamlead_wait` — **БЕЗ ЭТОГО СИСТЕМА НЕ РАБОТАЕТ**
2. Добавить кнопку "Ответить" после ответа TeamLead
3. Добавить индикатор загрузки и обработку ошибок
4. Фикс healthcheck URL
5. Фикс .env проброса в Docker

---

## АРХИТЕКТУРА ТЕКУЩЕГО СОСТОЯНИЯ

```
User → welcome.html (JS) → /api/teamlead_query (SSE) → agent_manager.py
→ model_router.py → Ollama (qwen3:8b, GPU) → ответ → SSE stream → welcome.html
```

Разрыв: ответ пользователя НЕ возвращается в API из-за пропущенной фазы.
