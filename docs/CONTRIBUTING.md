# 🤝 Как контрибьютить

## Форк и Clone

```bash
git fork https://github.com/yourname/ai-team-system
git clone https://github.com/yourname/ai-team-system
cd ai-team-system
```

## Создание ветки

```bash
git checkout -b feature/my-feature
```

## Коммиты

```bash
git add .
git commit -m "feat: добавить нового агента"
```

## Формат коммитов
- `feat:` — новая фича
- `fix:` — исправление бага
- `docs:` — документация
- `refactor:` — рефакторинг

## Push и Pull Request

```bash
git push origin feature/my-feature
```

Откройте PR на GitHub.

## Тестирование

```bash
pytest tests/
```

## Code style

```bash
ruff check .
```
