# Hustl Analyzer

Веб-сервис для анализа техники танца хастл по видео: локальный ритм и AI-разбор постуры, техники и музыкальности.

Python 3.11 · FastAPI 0.109.0 · React 18 · TypeScript 5 · Vite 5

ОС разработки — Windows. Команды ниже для PowerShell. Это уже рабочий каталог репозитория: клонировать ничего не нужно.

## Что умеет

- Регистрация, вход и выход. В профиле меняются отображаемое имя, email и пароль.
- Загрузка видео до 10 минут и 1 ГБ (`MAX_VIDEO_DURATION` = 600 с, `MAX_UPLOAD_SIZE` = 1 073 741 824 байт).
- Перед анализом выбирают, кого разбирать: девушку, мужчину или обоих.
- Локальный ритм без AI: MediaPipe (33 точки скелета) и librosa. Метаданные, звук и кадры снимают `ffprobe` и `ffmpeg`.
- AI-оценки постуры, техники и музыкальности. Провайдер — `AI_PROVIDER`. По умолчанию и в текущей конфигурации `grok_cli`: локальный Grok CLI, вход через `grok login` по подписке. Ключ API и свой адрес сервера в этот вызов не передаются. Остаются `claude_cli` (подписка Claude Code) и `claude` (официальный API Anthropic, пакет `anthropic` 0.18.1, без своего базового URL).
- Если AI недоступен, анализ завершается с оценкой ритма. Постура, техника и музыкальность остаются пустыми.
- Общая оценка — среднее по тем категориям, которые удалось посчитать.
- Не больше 10 ошибок после объединения ритма и AI: элемент, время, тип, серьёзность, описание. Скриншот — кадр пользователя, снятый ffmpeg, с красным скелетом и, если найдена похожая поза, серый холст `REFERENCE_BG` с зелёным скелетом рядом. Текста на картинке нет: замечание и «Как исправить» остаются в карточке.
- На странице результата анализ можно сохранить в историю или отбросить. В истории — имя файла, оценки, превью скриншота и удаление.
- В профиле — средние оценки, топ-3 типов ошибок и график по сохранённым анализам.

Эталоны: в `hasl_files` 648 видеофайлов и 647 уникальных элементов. Позы — 647 JSON в `backend/data/reference_poses`. Один MOV — намеренный дубликат одноимённого mp4 и отдельно не извлекается.

## Страницы

| Путь | Кто видит |
|---|---|
| `/login`, `/register` | гости; вошедших перенаправляет на `/upload` |
| `/upload` | нужен вход; сюда же ведут `/` и неизвестные пути |
| `/processing/:analysisId` | ход обработки |
| `/results/:analysisId` | результат, сохранение или отбрасывание |
| `/history` | сохранённые анализы |
| `/profile` | аккаунт и статистика |

Интерфейс: http://127.0.0.1:3000. Клиент `frontend/src/services/api.ts` вызывает `VITE_API_URL` или, если переменной нет, `http://localhost:8000`. Прокси `/api` в `frontend/vite.config.ts` на `http://127.0.0.1:8000` есть, но приложение его не использует.

## Стек

**Backend.** Python 3.11, FastAPI 0.109.0, Uvicorn 0.27.0, SQLAlchemy 2.0.25, Alembic 1.13.1, Celery 5.3.6, Redis (клиент 5.0.1), PostgreSQL через psycopg2 2.9.9, Pydantic 2.5.3.

**Зрение и звук.** MediaPipe 0.10.33, OpenCV 4.9.0.80, librosa 0.10.1, FFmpeg.

**Данные.** PostgreSQL 15 и Redis 7 в Docker. На хосте PostgreSQL опубликован как **5433**, Redis — **6379**.

**Frontend.** По `frontend/package-lock.json`: React 18.3.1, TypeScript 5.9.3, Vite 5.4.21, Material-UI 5.18.0, Axios 1.20.0, Recharts 2.15.4. В `package.json` те же пакеты заданы диапазонами (`react` ^18.2.0, `vite` ^5.0.11 и остальные). Для Vite 5.4.21 нужен Node.js `^18.0.0 || >=20.0.0` (Node 19 не поддерживается).

## Запуск

Нужны Docker с командой `docker-compose`, Python 3.11, Node.js `^18.0.0 || >=20.0.0` (не 19), `ffmpeg` и `ffprobe` в `PATH`. Для `grok_cli` в `PATH` нужен Grok CLI (`grok`), уже вошедший командой `grok login`. Для `claude_cli` нужен вошедший Claude Code CLI. Для `claude` нужен ключ Anthropic.

Виртуальное окружение Python 3.11 уже лежит в `backend\venv`. Все команды backend выполняются из каталога `backend`: оттуда читается `.env`.

### 1. PostgreSQL и Redis

Из корня этого каталога:

```powershell
docker-compose up -d
```

Пользователь, пароль и имя базы — `POSTGRES_USER`, `POSTGRES_PASSWORD` и `POSTGRES_DB` в `docker-compose.yml`.

### 2. Файл `backend/.env`

Файла `backend/.env.example` нет. Создайте `backend/.env` вручную. Не коммитьте его и не копируйте сюда ключи.

```env
DATABASE_URL=postgresql://hustl_user:<POSTGRES_PASSWORD>@127.0.0.1:5433/hustl_db
REDIS_URL=redis://127.0.0.1:6379/0
SECRET_KEY=<своя строка, не короче 32 символов>
AI_PROVIDER=grok_cli
CORS_ORIGINS=["http://127.0.0.1:3000","http://localhost:3000"]
```

`<POSTGRES_PASSWORD>` — значение из `docker-compose.yml`. `SECRET_KEY` короче 32 символов или со фрагментом `your-super-secret-key` приложение отвергает.

Vite открывается как http://127.0.0.1:3000. Это другой origin, чем `http://localhost:3000`, поэтому дефолт `CORS_ORIGINS` и пример в `.env` включают оба адреса.

Для `grok_cli` ключ API не нужен и в процесс CLI не попадает. `GROK_CLI_PATH` по умолчанию `grok`. Пустой `GROK_CLI_MODEL` — модель подписки по умолчанию. `GROK_CLI_TIMEOUT` — 600 секунд. Вход: `grok login`.

Для `claude_cli` ключ API тоже не нужен. `CLAUDE_CLI_PATH` по умолчанию `claude`. Пустой `CLAUDE_CLI_MODEL` — модель подписки по умолчанию. `CLAUDE_CLI_TIMEOUT` — 600 секунд.

Для официального API: `AI_PROVIDER=claude` и непустой `ANTHROPIC_API_KEY`. Если `CLAUDE_MODEL` пустой, сервис запрашивает список моделей и берёт первую.

Остальные параметры (папки загрузок, лимиты, эталоны) заданы по умолчанию в `backend/app/config.py`.

### 3. Зависимости и миграции

Если каталога `backend\venv` нет, из `backend`:

```powershell
py -3.11 -m venv venv
```

Дальше из `backend`:

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
```

В bash активация другая: `source venv/bin/activate`.

`alembic upgrade head` включает ревизию `0003_user_display_name`.

### 4. API, воркер, интерфейс

Каждый блок — свой терминал из корня каталога. В `backend/app/main.py` нет блока `if __name__`: сервер запускается только через Uvicorn. Без воркера загрузка встаёт в очередь и не обрабатывается (`process_video_task.delay`).

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
cd backend
.\venv\Scripts\Activate.ps1
celery -A app.core.celery_app worker --loglevel=info --pool=solo
```

На Windows воркеру обязателен `--pool=solo`.

Планировщик не обязателен. Раз в час он удаляет просроченные временные загрузки (срок — `TEMP_UPLOAD_TTL_HOURS`, по умолчанию 24):

```powershell
cd backend
.\venv\Scripts\Activate.ps1
celery -A app.core.celery_app beat --loglevel=info
```

Фронтенд:

```powershell
cd frontend
npm install
npm run dev
```

Открыть:

- интерфейс: http://127.0.0.1:3000
- API: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/api/docs
- ReDoc: http://127.0.0.1:8000/api/redoc
- проверка: http://127.0.0.1:8000/health

## API

Схема собирается из кода. Ниже только маршруты; модели запросов и ответов — в Swagger, ReDoc и OpenAPI.

- Swagger: http://127.0.0.1:8000/api/docs
- ReDoc: http://127.0.0.1:8000/api/redoc
- OpenAPI JSON: http://127.0.0.1:8000/api/openapi.json

Адреса `/docs` нет.

`POST /api/auth/login` принимает `application/x-www-form-urlencoded`: поле `username` — это email, поле `password` — пароль. В ответе есть `access_token`.

Защищённые маршруты требуют заголовок `Authorization: Bearer <token>`.

Поток видео и скриншот ошибки принимают тот же токен ещё и как `?token=`: тег браузера не может отправить заголовок. Остальные маршруты query-токен не принимают.

| Метод | Путь | Доступ | Назначение |
| --- | --- | --- | --- |
| GET | `/` | нет | Имя сервиса, версия и ссылка на документацию |
| GET | `/health` | нет | Проверка, что процесс отвечает |
| POST | `/api/auth/register` | нет | Регистрация по email и паролю |
| POST | `/api/auth/login` | нет | Вход, в ответе `access_token` |
| GET | `/api/users/me` | Bearer | Текущий профиль |
| PUT | `/api/users/me` | Bearer | Обновить email, пароль или имя |
| GET | `/api/users/stats` | Bearer | Сводка по сохранённым анализам |
| DELETE | `/api/users/me` | Bearer | Удалить аккаунт и связанные данные |
| POST | `/api/videos/` | Bearer | Загрузить видео (обязательное поле `subject`: `female`, `male` или `both`) и поставить анализ в очередь |
| GET | `/api/videos/` | Bearer | Список своих видео |
| GET | `/api/videos/history` | Bearer | Только сохранённые видео |
| GET | `/api/videos/{video_id}` | Bearer | Одно своё видео |
| GET | `/api/videos/{video_id}/stream` | Bearer или ?token= | Отдать файл для плеера |
| DELETE | `/api/videos/{video_id}` | Bearer | Удалить видео, файл и анализы |
| GET | `/api/analyses/` | Bearer | Список своих анализов |
| GET | `/api/analyses/{analysis_id}` | Bearer | Анализ вместе с ошибками |
| GET | `/api/analyses/{analysis_id}/status` | Bearer | Короткий статус для опроса |
| GET | `/api/analyses/{analysis_id}/errors` | Bearer | Ошибки анализа постранично |
| GET | `/api/analyses/{analysis_id}/errors/{error_id}/screenshot` | Bearer или ?token= | JPEG кадра ошибки |
| POST | `/api/analyses/{analysis_id}/save` | Bearer | Сохранить результат навсегда |
| DELETE | `/api/analyses/{analysis_id}` | Bearer | Удалить анализ, видео и скриншоты |

## Структура

Документы лежат в корне репозитория, не в каталоге `docs/`.

```
./
├── backend/
│   ├── app/
│   │   ├── api/            # auth, users, videos, analyses
│   │   ├── core/           # Celery, JWT
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── tasks/
│   │   ├── utils/          # ffprobe / ffmpeg
│   │   ├── config.py
│   │   └── main.py
│   ├── alembic/versions/   # до 0003_user_display_name
│   ├── data/
│   │   ├── reference_poses/    # 647 JSON
│   │   └── reference_index.json
│   ├── scripts/
│   ├── tests/
│   ├── requirements.txt
│   └── venv/               # Python 3.11
├── frontend/src/
│   ├── pages/
│   ├── components/
│   ├── services/
│   ├── hooks/
│   └── types/
├── hasl_files/             # 648 видео, 647 уникальных элементов
├── docker-compose.yml
├── ARCHITECTURE.md
├── CHECKLIST.md
├── CONTEXT.md
├── PROGRESS.md
└── README.md
```

## Документация

- [USER_GUIDE.md](./USER_GUIDE.md) — как пользоваться интерфейсом
- [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) — устройство кода
- [DIPLOMA.md](./DIPLOMA.md) — техническое описание для диплома
- [CONTEXT.md](./CONTEXT.md) — контекст проекта
- [ARCHITECTURE.md](./ARCHITECTURE.md) — архитектура
- [FULL_MVP_PLAN.md](./FULL_MVP_PLAN.md) — план MVP
- [CHECKLIST.md](./CHECKLIST.md) — список задач
- [PROGRESS.md](./PROGRESS.md) — что уже запускалось
- [DEVELOPMENT_LOG.md](./DEVELOPMENT_LOG.md) — журнал

Роли агентов: [AGENT_ROLES.md](./AGENT_ROLES.md), [ORCHESTRATOR_PROMPT.md](./ORCHESTRATOR_PROMPT.md), [DEVELOPER_PROMPT.md](./DEVELOPER_PROMPT.md), [REVIEWER_PROMPT.md](./REVIEWER_PROMPT.md).

Живая схема API — http://127.0.0.1:8000/api/docs и http://127.0.0.1:8000/api/redoc. Отдельного `/docs` нет.

## Разработка

Из `backend`, с активным venv:

```powershell
alembic revision --autogenerate -m "описание"
alembic upgrade head
alembic downgrade -1
pytest
pytest --cov=app
```

Из `frontend`:

```powershell
npm run dev
npm run build
npm run lint
npm run format
```

Скрипта тестов у фронтенда нет.

Docker, из корня:

```powershell
docker-compose logs -f
docker-compose restart
docker-compose down
```

`docker-compose down -v` удаляет тома PostgreSQL и Redis вместе с данными.

## Проект

Дипломный проект. Состояние задач — в [CHECKLIST.md](./CHECKLIST.md) и [PROGRESS.md](./PROGRESS.md).

Дата последнего обновления: 13 ноября 2026.
