# Блог с комментариями

## Описание
Блог-платформа с постами и комментариями.

## Требования
- Flask + SQLAlchemy
- SQLite
- CRUD для постов
- Комментарии к постам
- Простой HTML интерфейс

## Модели

### Post
- id (int, PK)
- title (string)
- content (text)
- created_at (datetime)

### Comment
- id (int, PK)
- content (text)
- post_id (int, FK → Post)
- created_at (datetime)

## Endpoints
- GET / — Главная (список постов)
- GET /post/{id} — Пост + комментарии
- POST /post — Создать пост
- POST /post/{id}/comment — Добавить комментарий
- DELETE /post/{id} — Удалить пост

## Фронтенд
- index.html — список постов
- post.html — пост + комментарии
- Простой CSS

## Тесты
- pytest для CRUD
- Тест комментариев

## Инфраструктура
- Dockerfile
- requirements.txt
