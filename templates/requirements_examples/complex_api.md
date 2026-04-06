# REST API для управления пользователями

## Описание
Backend API сервис с аутентификацией и CRUD операциями.

## Требования

### Endpoints
- POST /api/auth/register — Регистрация
- POST /api/auth/login — Вход (JWT)
- GET /api/users — Список пользователей
- GET /api/users/{id} — Один пользователь
- PUT /api/users/{id} — Обновление
- DELETE /api/users/{id} — Удаление

### Модель User
```json
{
  "id": "uuid",
  "email": "string",
  "name": "string",
  "password_hash": "string",
  "created_at": "datetime"
}
```

### Авторизация
- JWT токены
- Refresh token
- Password hashing (bcrypt)

### Валидация
- Email формат
- Password минимум 8 символов
- Unique email

## Стек
- Python / FastAPI
- PostgreSQL / SQLite
- SQLAlchemy
- Pydantic
- PyJWT

## Тесты
- Unit тесты на CRUD
- Тест авторизации
- Интеграционные тесты

## Деплой
- Docker контейнер
- Docker Compose (app + db)
