# 🔧 Решение проблем

## Ollama не работает

### Проверка
```bash
curl http://localhost:11434/api/tags
```

### Если не запущена
```bash
ollama serve
```

### Если модель не загружается
```bash
ollama pull qwen2.5-coder:7b
```

## Нет VRAM для модели

- Используйте меньшую модель (7B вместо 13B)
- Уменьшите `num_ctx` в конфиге
- Используйте Q4 квантизацию

## Агенты не работают

1. Проверьте логи: `~/.logs/ai_team/`
2. Убедитесь, что контекст >= 8K
3. Попробуйте профиль `light`

## Медленная генерация

- Используйте GPU вместо CPU
- Уменьшите `num_ctx`
- Используйте API вместо Ollama

## Import errors

```bash
pip install -r requirements.txt --upgrade
```

## Web UI не открывается

```bash
python -c "from flask import Flask; print('Flask OK')"
```

Проверьте, занят ли порт 5000:
```bash
lsof -i :5000
```
