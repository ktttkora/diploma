# 📊 ПРОГРЕСС РАЗРАБОТКИ

**Обновлено:** 14 ноября 2026

## 14 ноября 2026 — фильтр ошибок по партнёру

На странице результата, когда в списке есть девушка и мужчина, переключатель «Кто» оставляет карточки и метки плеера одного человека. Ошибки без метки остаются на «Все». Фильтр хранится на странице: сохранение результата его не сбрасывает.

- Developer: `ErrorsList.tsx`, `ResultsPage.tsx`
- Reviewer: REQUEST_CHANGES (фильтр жил в двух местах и расходился после сохранения; `NaN !== NaN` крутил бы рендер)
- Правки внесены. `tsc --noEmit` без ошибок

## 14 ноября 2026 — выбор партнёра

На загрузке обязателен выбор: девушка, мужчина или оба. Анализ хранит `subject`, ошибка — `person`. Промпт просит отличать людей по внешности. Ошибки другого партнёра отбрасываются. Пустая метка при выборе одного человека сохраняется и помечается выбранным полом. MediaPipe по-прежнему видит одно тело.

- Developer: модели, миграция `0004_analysis_subject`, промпт, API, экраны загрузки, результата и истории, тесты
- Reviewer: REQUEST_CHANGES (пустую метку нельзя выбрасывать; `server_default` без лишних кавычек)
- Developer: обе правки внесены. `pytest` по тестам субъекта и промпта — 14 passed

API на `http://127.0.0.1:8000/health` отвечает `healthy`. Celery `celery@kttt ready`. Интерфейс на порту 3000 отдаёт 200. Провайдер AI — `grok_cli`.

## 13 ноября 2026 — задача 31.1

README приведён к коду: Python 3.11, Uvicorn, PostgreSQL на порту 5433, API `/api/docs`, провайдеры `claude` и `claude_cli`, 648 роликов / 647 JSON.

- Developer: README и запись в DEVELOPMENT_LOG.md
- Reviewer: REQUEST_CHANGES (холст эталона, реальный URL клиента, Node.js без версии 19)
- Developer: три правки внесены, повторная сверка с кодом — принято

## 13 ноября 2026 — задача 31.2

В README добавлен раздел «API»: 21 маршрут из кода, Swagger `/api/docs`, ReDoc `/api/redoc`, OpenAPI `/api/openapi.json`. Отдельного `/docs` нет. `?token=` только у потока видео и скриншота ошибки.

- Developer: раздел в README и строка в DEVELOPMENT_LOG.md
- Reviewer: APPROVE

## 13 ноября 2026 — задачи 31.3–31.15, кроме скриншотов

- `USER_GUIDE.md` — сценарии экранов и FAQ по фактическим кнопкам.
- `DEVELOPER_GUIDE.md` — текущий поток данных, каталоги, ограничения.
- `DIPLOMA.md` — постановка, обзор, схема, прогон тестов, выводы.
- Тесты: 157 passed, покрытие `app` 65%.

## 13 ноября 2026 — стек запущен, скриншоты сняты

Миграция `0003` применена. API, Celery и Vite работают. Интерфейс на `127.0.0.1:3000` не попадал в CORS, из-за этого страницы не загружали данные. В `CORS_ORIGINS` добавлен `http://127.0.0.1:3000`.

Снимки лежат в `screenshots/`. Разбор короткого ролика дошёл до конца локально. Claude CLI ответил `Not logged in · Please run /login`, поэтому оценки AI пустые.

Не начато: неделя презентации и защиты. Для AI нужен вход в Claude CLI.

## Личный кабинет (неделя 8)

В коде не было профиля, статистики и общего меню, хотя чеклист отмечал их готовыми. Добавлено:

- `GET /api/users/stats` — средние оценки, топ-3 типов ошибок, ряд оценок по сохранённым анализам
- Поле `users.display_name` и правка имени, email и пароля на `/profile`
- График прогресса и общая шапка (Загрузить, История, Профиль)
- История: имя файла, оценки по категориям, превью скриншота, удаление

Перед запуском применить миграцию: `alembic upgrade head` (ревизия `0003_user_display_name`). Docker в этой сессии не был запущен, миграция на живую БД не накатывалась.

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
- GLM и прокси Octava удалены из кода и из `.env`
- Рабочий провайдер: `AI_PROVIDER=claude_cli`

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
