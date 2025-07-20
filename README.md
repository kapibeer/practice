# Микросервисы Movies и Users

## Описание

Два микросервиса на FastAPI:

- `movies` — управление данными о фильмах, жанрах и актёрах.
- `users` — управление пользователями и их оценками.

## Запуск проекта

1. Убедитесь, что установлен Docker и Docker Compose.
2. В директориях movies, users соответственно соберите образы:
 ```bash
docker build . -t movies
```
 ```bash
docker build . -t users
```
3. В корне проекта выполните:
```bash
docker-compose up -d
```

## Документация
1. [Movies Docs](http://localhost:8000/docs)
2. [Users Docs](http://localhost:8001/docs)

