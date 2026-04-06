# Fullstack приложение — Блог

## Описание
Блог-платформа с админкой.

## Frontend

### Страницы
- Главная — список постов
- Пост — полный текст
- Создание/редактирование поста
- Авторизация/регистрация
- Админ-панель

### Функционал
- Markdown редактор
- Загрузка изображений
- Комментарии
- Теги/категории
- Поиск

## Backend

### API Endpoints
- Auth: register, login, logout
- Posts: CRUD, list, detail
- Comments: CRUD
- Categories: CRUD
- Tags: CRUD
- Media: upload

### Модели
- User (id, email, password, role)
- Post (id, title, content, author_id, published)
- Comment (id, content, post_id, user_id)
- Category (id, name, slug)
- Tag (id, name, slug)

## Стек

### Frontend
- React 18
- React Router
- Axios
- Tailwind CSS

### Backend
- Node.js / Express
- PostgreSQL
- Prisma ORM
- JWT auth

## Инфраструктура
- Docker + Docker Compose
- Nginx (reverse proxy)
- CI/CD с GitHub Actions

## Тесты
- Jest для фронта
- Supertest для API
- E2E с Playwright
