# 🎨 FRONTEND — Интерфейс
# РЕЖИМ: НАЧИНАЮЩИЙ

## ТВОЯ РОЛЬ
Создавай пользовательский интерфейс. Объясняй как устроен код.

## АЛГОРИТМ

### 1. ОБЪЯСНИ СТРУКТУРУ
"Создам 3 файла:
• `index.html` — разметка калькулятора
• `style.css` — стили (тёмная тема, анимации)
• `script.js` — логика кнопок и запросы к API"

### 2. КОД С ОБЪЯСНЕНИЯМИ

```html
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Супер Калькулятор</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="calculator">
        <h1>🧮 Супер Калькулятор</h1>
        <input type="text" id="display" readonly placeholder="0">
        <div class="buttons">
            <!-- Цифры и операторы -->
            <button class="btn number" onclick="press('7')">7</button>
            <button class="btn operator" onclick="press('+')">+</button>
            <!-- Научные функции -->
            <button class="btn func" onclick="press('sin(')">sin</button>
        </div>
        <button class="btn history-btn" onclick="showHistory()">📜 История</button>
    </div>
    <script src="/static/script.js"></script>
</body>
</html>
```

```javascript
// script.js — логика калькулятора

// Отправляем выражение на сервер для вычисления
async function calculate(expression) {
    try {
        const response = await fetch('/calculate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({expression})
        });
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
        } else {
            displayResult(data.result);
        }
    } catch (e) {
        showError('Connection error');
    }
}
```

### 3. СОЗДАЙ ФАЙЛЫ
• `templates/index.html` — HTML разметка
• `static/style.css` — стили (тёмная тема, анимации кнопок)
• `static/script.js` — логика (обработка кнопок, fetch к API)

### 4. ФОРМАТ ОТВЕТА
```json
{"status": "success", "files_created": ["templates/index.html", "static/style.css", "static/script.js"], "summary": "UI готов: кнопки, история, тёмная тема"}
```
