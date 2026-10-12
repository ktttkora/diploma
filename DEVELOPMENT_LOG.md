# 📋 ЖУРНАЛ РАЗРАБОТКИ

## Сессия: 12 октября 2026

### Выполнено

**Инфраструктура:**
- Git репозиторий инициализирован в `code/` (не в домашней папке!)
- Структура папок backend/frontend создана
- `.gitignore` настроен
- Docker Compose (PostgreSQL 15 + Redis 7) - PostgreSQL проброшен на **порт 5433**

**Backend (Неделя 1-2):**
- 5 моделей БД: User, Video, Analysis, Error, TempUpload
- Auth API: register, login, get/update/delete me
- Video API: upload, list, get, delete
- Analysis API: list, get, errors, delete
- 6 сервисов: storage, audio, pose, rhythm, claude, reference, visualization
- Celery задачи: process_video_task, cleanup_expired_uploads
- Alembic миграции применены
- FastAPI сервер работает на :8000

**Frontend (Неделя 2):**
- React 18 + TypeScript + Vite + MUI
- Auth UI: LoginPage, RegisterPage, UploadPage
- Сервисы: api, authService, videoService, analysisService
- Роутинг с PrivateRoute/PublicRoute

### Проверено E2E
- ✅ `/health` → 200
- ✅ Регистрация через API → создан user id=1
- ✅ Логин → получен JWT токен
- ✅ `/api/users/me` с токеном → профиль
- ✅ `/api/docs` → 200, все эндпоинты видны
- ✅ Таблицы в PostgreSQL созданы

---

## 🚨 ПРОБЛЕМЫ И РЕШЕНИЯ

### 1. Python 3.14 вместо 3.11
**Проблема:** Системный Python 3.14.7, под него нет prebuilt wheels для pydantic-core, psycopg2, pillow.
**Решение:** Пересоздан venv на Python 3.11.9 (`py -3.11 -m venv venv`).

### 2. passlib + bcrypt 5.x несовместимость
**Проблема:** `ValueError: password cannot be longer than 72 bytes` при регистрации.
**Решение:** `pip install bcrypt==4.0.1` (passlib 1.7.4 не работает с bcrypt 5.x).

### 3. Порт 5432 занят локальным PostgreSQL 18
**Проблема:** Docker PostgreSQL не мог занять порт.
**Решение:** Docker PostgreSQL переведён на **5433**, `.env` обновлён.

### 4. Асинхронный SQLAlchemy + psycopg2
**Проблема:** Изначально код был на async engine, но psycopg2 - sync драйвер.
**Решение:** Весь код переведён на sync SQLAlchemy (проще для MVP).

### 5. extra="forbid" в pydantic-settings
**Проблема:** Лишние переменные в .env (`UPLOAD_DIR`, `MAX_FILE_SIZE`) вызывали ошибку.
**Решение:** `.env` приведён в соответствие с `Settings` (`UPLOAD_FOLDER`, `TEMP_FOLDER`, `SCREENSHOTS_FOLDER`, `MAX_UPLOAD_SIZE`).

---

## ❌ НЕ ВЫПОЛНЕНО (блокеры)

### Датасет эталонов нерабочий
**Факт:** В `code/hasl_files/` 670 файлов с расширением `.mp4`, но все по 3-7 КБ.
**Причина:** Это WebP-превьюшки из сохранённой HTML-страницы `Техника.html`. Настоящие видео не скачались.
**Проверка:** Первые байты файла - `RIFF....WEBPVP8`, а не MP4-контейнер.
**Следствие:** Задачи 1.5, 3.1, 3.2 (ReferenceService) заблокированы.

**Что нужно:** Скачать настоящие видео элементов хастла, либо найти другой источник эталонов.

### Тестовое видео
`code/test/video_2026-10-11_13-32-56.mp4` - настоящее (13.5 МБ, 720x1280, 42.8с, h264+aac).

---

## 📝 ЗАМЕТКИ

- Anthropic API ключ в `.env` - placeholder, нужен настоящий для Claude-анализа
- Celery worker/beat не запускались (нужны для реальной обработки)
- Frontend `npm install` в процессе
