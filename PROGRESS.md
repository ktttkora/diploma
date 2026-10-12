# 📊 ПРОГРЕСС РАЗРАБОТКИ

**Обновлено:** 12 октября 2026

## Общий статус: Недели 1-2 завершены, система работает E2E

```
Неделя 1  ██████████  ✅ Подготовка (кроме датасета)
Неделя 2  ██████████  ✅ Backend Core + Auth + Video/Analysis API
Неделя 3  █████░░░░░  ⏳ Claude API (код готов, нужен API-ключ)
Неделя 4+ ░░░░░░░░░░  ⏳ Не начато
```

---

## ✅ Что работает прямо сейчас

### Backend (порт 8000)
- FastAPI сервер: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/api/docs`
- 10 API эндпоинтов (auth, users, videos, analyses)
- PostgreSQL 15 в Docker (порт 5433), 5 таблиц создано
- Redis 7 в Docker (порт 6379)

### Frontend (порт 3000)
- Vite dev сервер: `http://127.0.0.1:3000`
- Login, Register, Upload страницы
- Прокси `/api` → backend

### Проверено E2E
| Тест | Результат |
|---|---|
| `/health` | ✅ 200 |
| Регистрация | ✅ 201, user создан |
| Логин | ✅ JWT токен получен |
| `/api/users/me` | ✅ профиль возвращён |
| Загрузка видео (13.5 МБ) | ✅ 201, duration определён |
| Анализ ритма (реальное видео) | ✅ 136 BPM, 94 бита, 37 шагов, 62.2% точность |
| MediaPipe детекция поз | ✅ 1269 кадров из ~1278 |
| Backend unit-тесты | ✅ 32/32 passed |
| Frontend build | ✅ без ошибок TS |
| Celery worker | ✅ подключается к Redis, 3 задачи зарегистрированы |

---

## ⛔ Блокеры

### 1. Датасет эталонов нерабочий (КРИТИЧНО)
- **Файлы:** `code/hasl_files/` — 670 файлов `.mp4` по 3-7 КБ
- **Реальность:** это WebP-превьюшки (сигнатура `RIFF....WEBPVP8`)
- **Причина:** сохранённая HTML-страница вместо скачанных видео
- **Блокирует:** задачи 1.5, 3.1-3.4 (ReferenceService без данных)
- **Решение:** скачать настоящие видео элементов хастла

### 2. Anthropic API ключ
- В `.env` placeholder `sk-ant-api03-your-key-here`
- **Блокирует:** Claude-анализ постуры/техники/музыкальности

---

## 🚀 Как запустить

```powershell
# 1. Docker (PostgreSQL 5433 + Redis 6379)
cd C:\Users\kt\important\university\diploma\code
docker-compose up -d

# 2. Backend
cd backend
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 3. Celery worker (отдельный терминал)
cd backend
.\venv\Scripts\Activate.ps1
celery -A app.core.celery_app worker --loglevel=info --pool=solo

# 4. Frontend (отдельный терминал)
cd frontend
npm run dev
```

Открыть: `http://127.0.0.1:3000`

---

## 📝 Важные технические решения

| Решение | Причина |
|---|---|
| Python 3.11 (не 3.14) | Нет prebuilt wheels для pydantic-core/psycopg2/pillow под 3.14 |
| Sync SQLAlchemy (не async) | Проще для MVP, psycopg2/psycopg - sync драйверы |
| mediapipe 0.10.9 | Версии 0.10.33+ и 1.x убрали legacy API `mp.solutions` |
| bcrypt 4.0.1 | passlib 1.7.4 несовместим с bcrypt 5.x |
| PostgreSQL на 5433 | Порт 5432 занят локальным PostgreSQL 18 |
| Lazy engine creation | Позволяет импортировать модули без активной БД |
