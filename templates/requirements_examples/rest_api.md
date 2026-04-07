# REST API на FastAPI

## Описание
REST API с аутентификацией и CRUD операциями.

## Требования
- FastAPI + SQLAlchemy
- JWT аутентификация
- PostgreSQL
- CRUD для пользователей и постов
- Docker + docker-compose

## Модели

### User
- id (int, PK)
- email (string, unique)
- name (string)
- hashed_password (string)
- created_at (datetime)

### Post
- id (int, PK)
- title (string)
- content (text)
- author_id (int, FK → User)
- created_at (datetime)

## Endpoints

### Auth
- POST /auth/register — Регистрация
- POST /auth/login — Вход (JWT)

### Users
- GET /users/ — Список
- GET /users/{id} — Один
- PUT /users/{id} — Обновить
- DELETE /users/{id} — Удалить

### Posts
- GET /posts/ — Список
- POST /posts/ — Создать
- GET /posts/{id} — Один
- PUT /posts/{id} — Обновить
- DELETE /posts/{id} — Удалить

## Тесты
- Unit тесты на CRUD
- Тест авторизации
- Интеграционные тесты

## Инфраструктура
- Dockerfile
- docker-compose.yml (app + db)
- .env.example
