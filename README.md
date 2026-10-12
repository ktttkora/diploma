# 🎭 Hustl Analyzer

Веб-сервис для автоматического анализа техники танца хастл с использованием AI.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue.svg)](https://www.typescriptlang.org/)

---

## 📋 Содержание

- [Описание](#описание)
- [Возможности](#возможности)
- [Технологии](#технологии)
- [Быстрый старт](#быстрый-старт)
- [Структура проекта](#структура-проекта)
- [Документация](#документация)
- [Разработка](#разработка)

---

## 📖 Описание

**Hustl Analyzer** помогает танцорам хастла улучшить технику через автоматический AI-анализ видео.

### Проблема
- Тренеры по хастлу дорогие и не всегда доступны
- Ручной анализ видео требует времени и экспертизы
- Нет автоматизированных инструментов для самостоятельного обучения

### Решение
Загрузи видео танца → получи детальный анализ с:
- 📊 Оценками по 4 категориям (ритм, постура, техника, музыкальность)
- 🎯 Топ-10 ошибок с подробным описанием
- 🖼️ Скриншотами с визуализацией (красный/зелёный скелет)
- 💡 Конкретными рекомендациями по исправлению

---

## ✨ Возможности

### Для пользователей
- 🎥 Загрузка видео (до 10 минут, до 1 GB)
- ⏱️ Обработка за 3-5 минут
- 📈 Оценки: ритм, постура, техника, музыкальность
- 📝 Топ-10 ошибок с описанием и рекомендациями
- 🖼️ Визуализация ошибок (композитные скриншоты)
- 💾 Сохранение результатов в историю
- 📊 Отслеживание прогресса

### Технические
- 🎵 Локальный анализ ритма (MediaPipe + librosa)
- 🤖 AI анализ постуры/техники (Claude Opus 5.5)
- 🎨 Автоматическая генерация скриншотов с разметкой
- 📚 База из 520 эталонных элементов хастла
- 🔐 Аутентификация и личный кабинет

---

## 🛠️ Технологии

### Backend
- **Python 3.10+** - язык программирования
- **FastAPI 0.109** - веб-фреймворк
- **SQLAlchemy 2.0** - ORM
- **PostgreSQL 15** - база данных
- **Celery 5.3** - асинхронные задачи
- **Redis 7** - брокер очередей

### AI & Computer Vision
- **Anthropic Claude Opus 5.5** - анализ постуры и техники
- **MediaPipe 0.10** - определение поз (33 точки скелета)
- **OpenCV 4.9** - обработка видео
- **librosa 0.10** - анализ аудио и битов
- **FFmpeg** - извлечение аудио и кадров

### Frontend
- **React 18** - UI библиотека
- **TypeScript 5** - типизация
- **Material-UI** - компоненты
- **Axios** - HTTP клиент
- **Recharts** - графики

---

## 🚀 Быстрый старт

### Требования

- Python 3.10+
- Node.js 18+
- Docker и Docker Compose
- FFmpeg
- Git

### Установка

1. **Клонировать репозиторий**
```bash
git clone https://github.com/YOUR_USERNAME/hustl-analyzer.git
cd hustl-analyzer
```

2. **Настроить Backend**

```bash
cd backend

# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt

# Скопировать .env.example в .env
cp .env.example .env

# Отредактировать .env (добавить ANTHROPIC_API_KEY)
```

3. **Запустить базы данных**

```bash
docker-compose up -d
```

4. **Применить миграции**

```bash
cd backend
alembic upgrade head
```

5. **Запустить Backend**

```bash
# Терминал 1: FastAPI
cd backend
python -m app.main

# Терминал 2: Celery Worker
celery -A app.core.celery_app worker --loglevel=info

# Терминал 3: Celery Beat (опционально)
celery -A app.core.celery_app beat --loglevel=info
```

6. **Запустить Frontend**

```bash
cd frontend
npm install
npm run dev
```

7. **Открыть в браузере**

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 📁 Структура проекта

```
hustl-analyzer/
├── backend/                    # Backend (FastAPI)
│   ├── app/
│   │   ├── api/               # API endpoints
│   │   ├── models/            # SQLAlchemy модели
│   │   ├── services/          # Бизнес-логика
│   │   ├── tasks/             # Celery задачи
│   │   ├── core/              # Конфигурация
│   │   ├── db/                # База данных
│   │   ├── schemas/           # Pydantic схемы
│   │   └── utils/             # Утилиты
│   ├── data/
│   │   ├── reference_poses/   # Эталонные позы (520 элементов)
│   │   └── uploads/           # Загруженные видео
│   ├── scripts/               # Вспомогательные скрипты
│   ├── tests/                 # Тесты
│   └── requirements.txt
│
├── frontend/                   # Frontend (React + TypeScript)
│   ├── src/
│   │   ├── pages/             # Страницы
│   │   ├── components/        # Компоненты
│   │   ├── services/          # API клиенты
│   │   ├── hooks/             # Custom hooks
│   │   └── types/             # TypeScript типы
│   └── package.json
│
├── docs/                       # Документация
│   ├── ARCHITECTURE.md        # Архитектура системы
│   ├── FULL_MVP_PLAN.md       # План разработки (13 недель)
│   ├── CHECKLIST.md           # Список задач
│   ├── CONTEXT.md             # Контекст для AI помощников
│   ├── AGENT_ROLES.md         # Мультиагентная система
│   └── ...
│
├── docker-compose.yml         # PostgreSQL + Redis
└── README.md                  # Этот файл
```

---

## 📚 Документация

### Для разработчиков

- **[CONTEXT.md](./CONTEXT.md)** - Полный контекст проекта (начни отсюда!)
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Детальная архитектура системы
- **[FULL_MVP_PLAN.md](./FULL_MVP_PLAN.md)** - План разработки (13 недель)
- **[CHECKLIST.md](./CHECKLIST.md)** - Список всех задач (~260)

### Мультиагентная разработка

- **[AGENT_ROLES.md](./AGENT_ROLES.md)** - Роли агентов
- **[ORCHESTRATOR_PROMPT.md](./ORCHESTRATOR_PROMPT.md)** - Промпт для координатора
- **[DEVELOPER_PROMPT.md](./DEVELOPER_PROMPT.md)** - Промпт для разработчика
- **[REVIEWER_PROMPT.md](./REVIEWER_PROMPT.md)** - Промпт для ревьюера

### API Документация

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 💻 Разработка

### Backend разработка

```bash
cd backend

# Создать новую миграцию
alembic revision --autogenerate -m "Add new field"

# Применить миграции
alembic upgrade head

# Откатить миграцию
alembic downgrade -1

# Запустить тесты
pytest

# Проверить покрытие тестами
pytest --cov=app tests/
```

### Frontend разработка

```bash
cd frontend

# Запустить dev сервер
npm run dev

# Собрать production build
npm run build

# Запустить линтер
npm run lint

# Запустить форматирование
npm run format
```

### Полезные команды

```bash
# Просмотр логов Docker
docker-compose logs -f

# Перезапуск контейнеров
docker-compose restart

# Остановка всех сервисов
docker-compose down

# Очистка volumes
docker-compose down -v
```

---

## 🔐 Переменные окружения

Создайте файл `backend/.env`:

```env
# Database
DATABASE_URL=postgresql://hustl_user:hustl_pass_2026@localhost:5432/hustl_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-super-secret-key-change-in-production-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# File Storage
UPLOAD_DIR=data/uploads
MAX_FILE_SIZE=1073741824
MAX_VIDEO_DURATION=600

# CORS
CORS_ORIGINS=["http://localhost:3000"]
```

---

## 🧪 Тестирование

### Backend тесты

```bash
cd backend

# Все тесты
pytest

# С покрытием
pytest --cov=app tests/

# Конкретный файл
pytest tests/test_services.py

# С выводом print
pytest -s
```

### Frontend тесты

```bash
cd frontend

# Запустить тесты
npm test

# Тесты в watch режиме
npm test -- --watch
```

---

## 📊 Прогресс разработки

См. [CHECKLIST.md](./CHECKLIST.md) для детального списка задач.

**Текущий статус:**
- [x] Архитектура спроектирована
- [x] План разработки составлен
- [x] Документация подготовлена
- [ ] Backend реализуется
- [ ] Frontend реализуется
- [ ] Тестирование

---

## 🤝 Вклад в проект

Этот проект разрабатывается как дипломный проект.

Если вы хотите внести вклад:
1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменений (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

---

## 📝 Лицензия

Этот проект создан в образовательных целях.

---

## 👤 Автор

**Ваше Имя**
- Email: your.email@example.com
- GitHub: [@yourusername](https://github.com/yourusername)

**Научный руководитель:** [Имя руководителя]

---

## 🙏 Благодарности

- [Anthropic](https://www.anthropic.com/) за Claude API
- [Google MediaPipe](https://google.github.io/mediapipe/) за pose detection
- [librosa](https://librosa.org/) за audio analysis
- Все open source библиотеки, использованные в проекте

---

## 📞 Поддержка

Если у вас есть вопросы:
- Откройте [Issue](https://github.com/YOUR_USERNAME/hustl-analyzer/issues)
- Напишите на email: your.email@example.com

---

**Дата последнего обновления:** 11 октября 2026
