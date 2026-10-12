# 🤖 КОНТЕКСТ ПРОЕКТА ДЛЯ AI

**Прочитай этот файл перед началом любой работы над проектом!**

---

## 📋 ЧТО ЭТО ЗА ПРОЕКТ

**Hustl Analyzer** - веб-сервис для анализа техники танца хастл с использованием AI.

### Проблема
Танцорам хастла нужна обратная связь по технике, но:
- Тренеры дорогие
- Видео анализ вручную долгий
- Нет автоматизированных инструментов

### Решение
Загружаешь видео танца → AI анализирует → получаешь:
- Оценки (ритм, постура, техника, музыкальность)
- Топ-10 ошибок с описанием
- Скриншоты с красным/зелёным скелетом
- Рекомендации по исправлению

---

## 🏗️ АРХИТЕКТУРА (кратко)

```
Frontend (React) → API (FastAPI) → Celery Worker
                                        ↓
                                   3 параллельных процесса:
                                   1. Локальный анализ ритма (MediaPipe + librosa)
                                   2. Claude Opus 5.5 (постура/техника/музыкальность)
                                   3. Генерация скриншотов
                                        ↓
                                   PostgreSQL (результаты)
```

**Детали:** См. `ARCHITECTURE.md`

---

## 💻 ТЕХНОЛОГИЧЕСКИЙ СТЕК

### Backend
- **Python 3.10+**
- **FastAPI 0.109.0** - веб-фреймворк
- **SQLAlchemy 2.0.25** - ORM
- **Alembic** - миграции БД
- **Celery 5.3.6** - асинхронные задачи
- **Redis 7** - брокер Celery
- **PostgreSQL 15** - основная БД

### AI & Computer Vision
- **Anthropic Claude Opus 5.5** - анализ постуры/техники/музыкальности
- **MediaPipe 0.10.9** - определение поз (33 точки скелета)
- **OpenCV 4.9** - обработка видео
- **librosa 0.10.1** - анализ аудио и битов
- **FFmpeg** - извлечение аудио/кадров

### Frontend
- **React 18**
- **TypeScript 5**
- **Material-UI (MUI)** - UI компоненты
- **React Router** - роутинг
- **Axios** - HTTP клиент
- **Recharts** - графики
- **React Player** - видеоплеер

---

## 🎯 КЛЮЧЕВЫЕ АРХИТЕКТУРНЫЕ РЕШЕНИЯ

### 1. Анализ ритма: ЛОКАЛЬНО (не через AI)
- **Причина:** Точность, скорость, экономия токенов
- **Технологии:** MediaPipe (позы) + librosa (биты)
- **Результат:** JSON с ошибками ритма

### 2. Claude получает данные о ритме
- **Вариант B** (выбран): Claude видит ошибки ритма
- **Причина:** Контекстные рекомендации

### 3. Топ-10 ошибок по severity
- Если ошибок ≤ 10 → показываем все
- Если ошибок > 10 → берём топ-10 (critical > high > medium > low)

### 4. Один композитный скриншот
- Красный скелет (текущая поза) + зелёный скелет (правильная поза) НА ОДНОМ изображении
- ❌ **НЕ два отдельных файла!**

### 5. Эталонные позы: 520 видео обработаны заранее
- Все элементы хастла в `backend/data/reference_poses/*.json`
- MediaPipe уже извлёк позы из всех 520 видео

### 6. Распознавание элементов: Гибрид
- Claude пытается распознать → если не получилось → MediaPipe правила
- Элементы: Американка, Солнышко, Катапульта, Йoyo, Окошко, etc

### 7. Скорость: 3-5 минут (приемлемо для MVP)
- Пользователь видит прогресс-бар
- Оптимизация отложена

---

## 📁 СТРУКТУРА ПРОЕКТА

```
hustl-analyzer/
├── backend/
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   │   ├── auth.py    # POST /auth/register, /login
│   │   │   ├── users.py   # GET /users/me, PUT /users/me
│   │   │   └── videos.py  # POST /videos/upload, GET /analysis/{id}, POST /save, DELETE
│   │   ├── models/        # SQLAlchemy модели
│   │   │   ├── user.py
│   │   │   ├── video.py
│   │   │   ├── analysis.py
│   │   │   ├── error.py   # ❗ БЕЗ reference_screenshot_path
│   │   │   └── temp_upload.py
│   │   ├── services/      # Бизнес-логика
│   │   │   ├── audio_service.py      # librosa, биты музыки
│   │   │   ├── pose_service.py       # MediaPipe, определение поз и шагов
│   │   │   ├── rhythm_service.py     # Локальный анализ ритма
│   │   │   ├── claude_service.py     # Claude Opus 5.5
│   │   │   ├── visualization_service.py  # Генерация скриншотов
│   │   │   └── reference_service.py  # Работа с эталонами
│   │   ├── tasks/         # Celery задачи
│   │   │   ├── video_tasks.py    # process_video_task (ГЛАВНАЯ)
│   │   │   └── cleanup_tasks.py  # cleanup_expired_uploads
│   │   ├── core/          # Конфигурация
│   │   │   ├── celery_app.py
│   │   │   └── security.py
│   │   ├── db/            # База данных
│   │   │   └── session.py
│   │   ├── schemas/       # Pydantic схемы
│   │   │   └── user.py
│   │   └── utils/         # Утилиты
│   │       ├── video_utils.py     # FFmpeg обёртки
│   │       └── frame_extractor.py # Извлечение кадров
│   ├── data/
│   │   ├── reference_poses/  # 520 JSON файлов с эталонами
│   │   └── uploads/
│   │       ├── temp/      # Временные видео
│   │       └── saved/     # Сохранённые видео
│   ├── scripts/           # Вспомогательные скрипты
│   └── tests/             # Тесты
│
├── frontend/
│   └── src/
│       ├── pages/         # Страницы
│       │   ├── LoginPage.tsx
│       │   ├── RegisterPage.tsx
│       │   ├── UploadPage.tsx
│       │   ├── ProcessingPage.tsx
│       │   ├── ResultsPage.tsx
│       │   └── ProfilePage.tsx
│       ├── components/    # Компоненты
│       │   ├── VideoUploader.tsx
│       │   ├── ProcessingProgress.tsx
│       │   ├── VideoPlayer.tsx
│       │   ├── ErrorCard.tsx
│       │   ├── ErrorsList.tsx
│       │   └── ScoresSummary.tsx
│       ├── services/      # API клиенты
│       │   ├── api.ts
│       │   ├── authService.ts
│       │   └── videoService.ts
│       └── hooks/         # Custom hooks
│           └── usePolling.tsx
│
└── docs/                  # Документация
    ├── ARCHITECTURE.md    # Детальная архитектура
    ├── FULL_MVP_PLAN.md   # Пошаговый план (13 недель)
    ├── CHECKLIST.md       # Список задач
    └── CONTEXT.md         # Этот файл
```

---

## 🗄️ СХЕМА БАЗЫ ДАННЫХ

### Таблицы (5)

**Users**
- id, email, password_hash, name, avatar_url, created_at, updated_at

**Videos**
- id, user_id, original_filename, file_path, thumbnail_path
- duration, size, resolution, fps, format
- uploaded_at, **is_saved** (False = временное, True = сохранённое)

**Analyses**
- id, video_id, **status** (queued → processing → completed/failed)
- overall_score, rhythm_score, posture_score, technique_score, musicality_score
- total_errors, processing_time, ai_response, created_at, completed_at, error_message

**Errors** ❗ **ВАЖНО**
- id, analysis_id, timestamp, category, severity
- title, description, recommendation
- **screenshot_path** (ОДИН композитный скриншот)
- ❌ **НЕТ reference_screenshot_path** (убрали!)
- detected_element, created_at

**TempUploads**
- id, user_id, file_path, uploaded_at, **expires_at** (24 часа)
- Celery задача каждый час удаляет истёкшие

---

## 🔌 API ENDPOINTS

### Auth
- `POST /api/auth/register` - Body: {email, password, name?}
- `POST /api/auth/login` - Body: {email, password} → {access_token}
- `GET /api/users/me` - Headers: Authorization Bearer
- `PUT /api/users/me` - Body: {name?, avatar_url?}

### Videos & Analysis
- `POST /api/videos/upload` - multipart/form-data → {video_id, analysis_id, status}
- `GET /api/videos/analysis/{id}` - Получить результат анализа
- **`POST /api/videos/analyses/{id}/save`** ❗ - Сохранить (temp/ → saved/)
- **`DELETE /api/videos/analyses/{id}`** ❗ - Удалить видео + скриншоты
- `GET /api/videos/history` - Список сохранённых видео

---

## ⚙️ СЕРВИСЫ (Services Layer)

### AudioService (`app/services/audio_service.py`)
```python
analyze_audio(audio_path: str) -> Dict
  # → {tempo: float, beats: [timestamps], duration, sample_rate}

find_closest_beat(timestamp: float, beats: List[float]) -> Tuple[float, float]
  # → (closest_beat_time, difference)

is_on_beat(timestamp: float, beats: List[float], tolerance=0.15) -> bool
```

### PoseService (`app/services/pose_service.py`)
```python
extract_poses_from_video(video_path: str) -> List[Dict]
  # MediaPipe на всех кадрах
  # → [{frame, timestamp, landmarks: [33 точки], detected: bool}]

detect_steps(poses: List[Dict]) -> List[Dict]
  # По движению стоп
  # → [{timestamp, foot: 'left'|'right', type: 'step'}]

calculate_angles(landmarks: List[Dict]) -> Dict
  # → {spine_angle, left_knee_angle, right_knee_angle}
```

### RhythmService (`app/services/rhythm_service.py`)
```python
analyze_rhythm(video_path: str) -> Dict
  # 1. Извлекает аудио (FFmpeg)
  # 2. Определяет биты (librosa)
  # 3. Извлекает позы (MediaPipe)
  # 4. Определяет шаги
  # 5. Сопоставляет шаги с битами
  # → {tempo, total_beats, total_steps, accuracy, rhythm_score, errors: []}
```

### ClaudeService (`app/services/claude_service.py`)
```python
analyze_video(frames: List[bytes], rhythm_errors: List[Dict]) -> Dict
  # Отправляет 100 кадров JPEG + данные о ритме в Claude Opus 5.5
  # → {posture_score, technique_score, musicality_score, errors: []}
```

### ReferenceService (`app/services/reference_service.py`)
```python
get_reference(element_name: str) -> Optional[Dict]
  # Загружает JSON с эталонными позами
  # → {element, total_frames, fps, poses: []}

find_similar_pose(element_name: str, target_timestamp: float) -> Optional[Dict]
  # Находит похожую позу из эталона

list_available_elements() -> List[str]
  # → ['Американка', 'Солнышко', 'Катапульта', ...]
```

### VisualizationService (`app/services/visualization_service.py`)
```python
create_error_screenshot(
    video_path: str,
    timestamp: float,
    error_data: Dict,
    detected_element: Optional[str]
) -> str
  # 1. Извлекает кадр (FFmpeg)
  # 2. Рисует красный скелет (MediaPipe на этом кадре)
  # 3. Получает эталонную позу (если элемент распознан)
  # 4. Рисует зелёный скелет
  # 5. Рисует стрелки между точками
  # 6. Добавляет текст снизу (timestamp, описание, рекомендация)
  # → путь к сохранённому композитному скриншоту
```

---

## 🔄 CELERY: ГЛАВНАЯ ЗАДАЧА

### process_video_task (7 шагов)

**Файл:** `backend/app/tasks/video_tasks.py`

```python
@celery_app.task(bind=True)
def process_video_task(self: Task, video_id: int, video_path: str):
    # ШАГ 1: Локальный анализ ритма (~90 сек)
    rhythm_result = rhythm_service.analyze_rhythm(video_path)
    # → {tempo, beats, steps, accuracy, rhythm_score, errors: []}
    
    # ШАГ 2: Извлечь 100 ключевых кадров (~5 сек)
    frames = frame_extractor.extract_key_frames(video_path, 100)
    # → List[bytes] - JPEG изображения
    
    # ШАГ 3: Claude API (~30-60 сек)
    claude_result = claude_service.analyze_video(frames, rhythm_result['errors'])
    # → {posture_score, technique_score, musicality_score, errors: []}
    
    # ШАГ 4: Объединение ошибок
    all_errors = rhythm_result['errors'] + claude_result['errors']
    
    # ШАГ 5: Отбор топ-10 по severity
    all_errors.sort(key=lambda e: severity_priority(e['severity']))
    top_10_errors = all_errors[:10]
    
    # ШАГ 6: Генерация скриншотов (~30-60 сек) ❗ КРИТИЧНО!
    for err_data in top_10_errors:
        screenshot_path = visualization_service.create_error_screenshot(
            video_path, err_data['timestamp'], err_data, err_data.get('detected_element')
        )
        err_data['screenshot_path'] = screenshot_path
    
    # ШАГ 7: Сохранение в БД
    analysis.status = "completed"
    analysis.rhythm_score = rhythm_result['rhythm_score']
    analysis.posture_score = claude_result['posture_score']
    # ... сохранить все оценки
    
    for err_data in top_10_errors:
        error = Error(
            analysis_id=analysis.id,
            timestamp=err_data['timestamp'],
            category=err_data['category'],
            severity=err_data['severity'],
            description=err_data['description'],
            recommendation=err_data['recommendation'],
            screenshot_path=err_data['screenshot_path'],  # ← ОБЯЗАТЕЛЬНО!
            detected_element=err_data.get('detected_element')
        )
        db.add(error)
    
    db.commit()
```

**Время обработки (2-минутное видео):**
- Ритм: 90 сек
- Кадры: 5 сек
- Claude: 45 сек
- Скриншоты: 45 сек
- **ИТОГО: ~3 минуты**

---

## 🎨 FRONTEND: ОСНОВНЫЕ КОМПОНЕНТЫ

### UploadPage
- Drag & drop видео
- Валидация (формат, размер ≤1GB, длительность ≤10мин)
- Прогресс-бар загрузки
- Редирект на ProcessingPage

### ProcessingPage
- Прогресс-бар обработки
- Polling `GET /analysis/{id}` каждые 3 сек
- Статус: queued → processing → completed
- Редирект на ResultsPage при completed

### ResultsPage
- **VideoPlayer** - react-player с timeline
- **ErrorsList** - список топ-10 ошибок
- **ErrorCard** - карточка одной ошибки:
  - Композитный скриншот (красный + зелёный скелет)
  - Timestamp, категория, severity
  - Описание + рекомендация
  - Клик → перемотка видео
- **ScoresSummary** - оценки по 4 категориям
- Кнопки: "Сохранить" / "Не сохранять"

### ProfilePage
- Данные профиля
- История сохранённых видео
- График прогресса (recharts)

---

## 🚨 КРИТИЧЕСКИЕ МОМЕНТЫ (НЕ ЗАБЫТЬ!)

### ❌ ЧТО НЕЛЬЗЯ ДЕЛАТЬ:

1. **НЕ добавляй `reference_screenshot_path` в модель Error**
   - Был удалён! Только `screenshot_path` (один композитный скриншот)

2. **НЕ пропускай генерацию скриншотов в Celery задаче**
   - ШАГ 6 обязателен!

3. **НЕ забудь API endpoints для save/discard**
   - `POST /analyses/{id}/save`
   - `DELETE /analyses/{id}`

### ✅ ЧТО ОБЯЗАТЕЛЬНО:

1. **Генерация скриншотов ДО сохранения в БД**
   - Иначе `screenshot_path` будет None

2. **Переносить видео из temp/ в saved/ при сохранении**
   - `POST /analyses/{id}/save` должен делать `shutil.move()`

3. **Удалять файлы при отклонении**
   - `DELETE /analyses/{id}` удаляет видео + скриншоты

4. **Celery Beat для очистки временных файлов**
   - Задача `cleanup_expired_uploads` каждый час

---

## 📏 СОГЛАШЕНИЯ О КОДЕ

### Python
- **Style:** PEP 8, snake_case для функций/переменных
- **Type hints:** Обязательны для всех функций
- **Docstrings:** Для публичных методов
- **Imports:** Абсолютные (`from app.services...`)

### TypeScript
- **Style:** camelCase для переменных, PascalCase для компонентов
- **Components:** Functional (не классы)
- **Props:** Типизировать интерфейсами
- **Hooks:** Custom hooks с префиксом `use`

### Комментарии
- Код: на английском
- Описания ошибок для пользователя: на русском
- Docstrings: на английском

### Структура файлов
- Один класс/сервис = один файл
- Тесты рядом: `service.py` → `test_service.py`

---

## 📍 ТЕКУЩИЙ ЭТАП

**Смотри:** `CHECKLIST.md` - список всех задач с прогрессом

**План разработки:** `FULL_MVP_PLAN.md` - детальный план 13 недель

**Архитектура:** `ARCHITECTURE.md` - полная документация

---

## 🔧 ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ (.env)

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

## 🧪 ТЕСТИРОВАНИЕ

### Unit тесты
- Каждый сервис должен иметь тесты
- Используй pytest
- Цель: coverage 70%+

### E2E тесты
- Полный цикл: загрузка → обработка → результат
- Проверка UI flow

### Запуск
```bash
cd backend
pytest
pytest --cov=app tests/
```

---

## 🚀 БЫСТРЫЙ СТАРТ

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
docker-compose up -d  # PostgreSQL + Redis
alembic upgrade head
python -m app.main  # http://localhost:8000
```

### Celery
```bash
celery -A app.core.celery_app worker --loglevel=info
celery -A app.core.celery_app beat --loglevel=info
```

### Frontend
```bash
cd frontend
npm install
npm run dev  # http://localhost:3000
```

---

## 📚 ДОПОЛНИТЕЛЬНЫЕ ФАЙЛЫ

- **FULL_MVP_PLAN.md** - пошаговый план разработки (13 недель)
- **ARCHITECTURE.md** - детальная архитектура
- **CHECKLIST.md** - список всех задач (~260 задач)
- **PLAN_REVIEW_FIXES.md** - найденные проблемы и исправления

---

## 💡 ПРОМПТЫ ДЛЯ AI

### Создание нового сервиса
```
Создай сервис XService в backend/app/services/x_service.py
Требования:
- Следуй архитектуре из CONTEXT.md
- Type hints обязательны
- Добавь docstrings
- Методы: [список методов]
```

### Создание React компонента
```
Создай компонент XComponent в frontend/src/components/XComponent.tsx
Требования:
- TypeScript + Material-UI
- Functional component
- Props: [список props с типами]
```

### Исправление бага
```
В файле X есть баг Y.
Контекст проекта: см. CONTEXT.md
Архитектура: см. ARCHITECTURE.md
Исправь с учётом архитектуры.
```

---

**Этот файл - твоя шпаргалка. Сохрани его и возвращайся при любых вопросах!**

*Последнее обновление: 11 октября 2026*
