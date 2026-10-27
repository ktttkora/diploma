# 📊 ПРОГРЕСС РАЗРАБОТКИ

**Обновлено:** 27 октября 2026

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

## ✅ Эталоны и распознавание элементов (27 октября 2026)

- Датасет `code/hasl_files/`: 648 настоящих видео (13 ГБ), 647 уникальных элементов
- `backend/data/reference_poses/`: 647 JSON (1.16 ГБ, 625 тыс. поз), 0 ошибок, медиана детекции 99.7%
- `backend/data/reference_index.json`: компактный индекс (8 МБ, 24 позы на эталон), сборка 35 с
- В AI-запрос уходят каталог названий (574 после нормализации) + кадры 5-10 кандидатов по MediaPipe
- Self-retrieval на 40 эталонах (средняя половина клипа): top-1 80%, top-8 85%
- Backend unit-тесты: 130/130 passed

Пересборка эталонов и индекса:
```powershell
cd backend
.\venv\Scripts\python.exe scripts\extract_all_references.py --yes --workers 6
.\venv\Scripts\python.exe scripts\build_reference_index.py
```

---

## ⛔ Блокеры

### 1. AI API
- `AI_PROVIDER=glm` (glm-4.6v-flash): 24 октября отвечал `429 service overloaded`
- Octava-ключ (`ANTHROPIC_*`): `400 OctavaAPI error 2000`, `CLAUDE_MODEL` пустой
- Лимит числа изображений GLM (сейчас `AI_MAX_IMAGES=30`) не проверен

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
| `extract_all_references.py --workers 6` | 14 воркеров на длинных видео исчерпали RAM (31 ГБ) |
| Дубликаты эталонов: .mp4 > .mov | mp4 с вдвое большим битрейтом |
| Aspect ratio в сравнении поз | эталоны горизонтальные, видео пользователей вертикальные |
| Lazy engine creation | Позволяет импортировать модули без активной БД |
