# Chat Backend (FastAPI)

Backend чат-приложения с поддержкой обмена сообщениями в реальном времени через WebSocket.

Проект реализует серверную часть мессенджера: аутентификацию пользователей, управление комнатами и отправку сообщений с сохранением в базе данных.

---

## Функциональность

- Регистрация и авторизация пользователей
- JWT-аутентификация
- Получение текущего пользователя
- Создание и получение комнат
- Отправка и получение сообщений
- Обмен сообщениями в реальном времени через WebSocket
- Сохранение сообщений в базе данных
- Аутентификация WebSocket соединений

---

## Технологии

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- JWT (python-jose)
- WebSocket
- Docker

---

## Структура проекта

backend/
├── main.py
├── database.py
├── models.py
├── schemas.py
├── auth.py
├── websocket_manager.py

---

## Запуск проекта

1. Клонирование

git clone https://github.com/YAroslav10Ti/chat-app.git
cd chat-app/backend

---

2. Создание .env

Создай файл .env:

DATABASE_URL=postgresql://chatuser:chatpassword@127.0.0.1:5433/chatdb
SECRET_KEY=my_super_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

---

3. Установка зависимостей

pip install -r requirements.txt

---

4. Запуск базы данных

docker compose up -d

---

5. Запуск сервера

uvicorn main:app --reload

---

## API документация

http://127.0.0.1:8000/docs

---

## WebSocket

ws://127.0.0.1:8000/ws/rooms/{room_id}?token=JWT

---

## Возможные улучшения

- онлайн-статус пользователей
- отправка файлов
- кеширование (Redis)
- тесты

---

## Автор

Yaroslav10Ti