# Архитектура веб-сервиса анализа танца хастл

## Дата обновления: 11 октября 2026
## Статус: ФИНАЛЬНАЯ ВЕРСИЯ MVP

---

## 🎯 КЛЮЧЕВЫЕ АРХИТЕКТУРНЫЕ РЕШЕНИЯ

На основе детального анализа были приняты следующие решения:

### 1. AI Модель: Claude Opus 5.5 (вместо Gemini)
**Причина:** Лучшее качество анализа видео, поддержка 100+ изображений в одном запросе, более точные рекомендации.

### 2. Анализ ритма: Локально (MediaPipe + librosa)
**Причина:** Точность, скорость, независимость от AI API, экономия токенов.

### 3. Передача данных Claude: Вариант B (Claude получает данные о ритме)
**Причина:** Контекстные рекомендации, связь ошибок ритма с постурой/техникой.

### 4. Количество ошибок: Топ-10 по severity
**Логика:**
- Если ошибок ≤ 10 → показываем все
- Если ошибок > 10 → берём топ-10 самых критичных

### 5. Визуализация: Красный + зелёный скелет на одном изображении
**Причина:** Наглядность, простота, один файл вместо двух.

### 6. Эталонные позы: 520 видео обработаны заранее
**Причина:** Максимальная точность для всех элементов хастла.

### 7. Распознавание элементов: Гибрид (Claude + MediaPipe правила)
**Причина:** Баланс точности и надёжности.

### 8. Скорость обработки: 3-5 минут без оптимизаций
**Причина:** Приемлемо для MVP, пользователь видит прогресс-бар.

### 9. Email-уведомления: Не в MVP
**Причина:** Прогресс-бар достаточен, email можно добавить позже.

### 10. Оптимизация скорости: Отложена
**Причина:** MVP работает за 3-5 минут, этого достаточно для защиты.

---

## 1. Общая схема системы

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│                      (React + TS)                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Auth    │  │  Upload  │  │  Results │  │ Profile  │   │
│  │  Pages   │  │  Page    │  │  Page    │  │  Page    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│       │             │              │              │          │
│       └─────────────┴──────────────┴──────────────┘          │
│                         │ HTTP/REST API                      │
└─────────────────────────┼──────────────────────────────────┘
                          │
┌─────────────────────────┼──────────────────────────────────┐
│                    BACKEND                                   │
│                   (FastAPI)                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │ Auth API   │  │ Videos API │  │ Users API  │           │
│  └────────────┘  └────────────┘  └────────────┘           │
│         │              │                │                    │
│         └──────────────┴────────────────┘                    │
│                        │                                     │
│         ┌──────────────┴──────────────┐                     │
│         │      Celery Worker          │                     │
│         │   (Video Processing)        │                     │
│         └──────────────┬──────────────┘                     │
│                        │                                     │
│    ┌───────────────────┼───────────────────┐               │
│    │                   │                   │               │
│ ┌──▼──────┐  ┌────────▼────────┐  ┌──────▼──────┐        │
│ │ Rhythm  │  │ Claude Opus 5.5 │  │Visualization│        │
│ │ Service │  │   (API Call)     │  │  Service   │        │
│ │(Local)  │  │                  │  │            │        │
│ └─────────┘  └──────────────────┘  └────────────┘        │
│      │                                     │               │
│ MediaPipe + librosa              Reference Poses          │
│      │                                     │               │
└──────┼─────────────────────────────────────┼──────────────┘
       │                                     │
   ┌───▼─────┐                          ┌───▼─────┐
   │ Video   │                          │ 520 JSON│
   │ Files   │                          │ Files   │
   └─────────┘                          └─────────┘
       │                                     │
   PostgreSQL                          reference_poses/
```

---

## 2. Технологический стек

### Frontend
- **React 18** - UI библиотека
- **TypeScript** - типизация
- **Material-UI (MUI)** - компоненты
- **React Router** - роутинг
- **Axios** - HTTP клиент
- **Recharts** - графики статистики
- **React Player** - видеоплеер

### Backend
- **FastAPI** - веб-фреймворк
- **Python 3.10+**
- **SQLAlchemy** - ORM
- **Alembic** - миграции БД
- **Celery** - асинхронные задачи
- **Redis** - брокер для Celery

### AI & Computer Vision
- **Anthropic Claude Opus 5.5** - анализ постуры/техники/музыкальности
- **MediaPipe** - определение поз (33 точки скелета)
- **OpenCV** - обработка видео
- **librosa** - анализ аудио и битов
- **FFmpeg** - извлечение аудио/кадров

### Базы данных
- **PostgreSQL 15** - основная БД
- **Redis 7** - кеш и очередь Celery

### Инфраструктура
- **Docker + Docker Compose** - контейнеризация
- **Git** - контроль версий

---

## 3. Архитектура обработки видео

### 3.1. Полный цикл обработки

```
┌──────────────────────────────────────────────────────────┐
│ 1. ЗАГРУЗКА ВИДЕО (Frontend → Backend)                   │
│    - Валидация: формат, размер (≤1GB), длительность (≤10мин) │
│    - Сохранение в temp/ папку                            │
│    - Создание записей: Video, TempUpload, Analysis       │
│    - Запуск Celery задачи                                │
└──────────────────┬───────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────┐
│ 2. CELERY ЗАДАЧА: process_video_task                     │
│                                                           │
│  ШАГ 1: Локальный анализ ритма (~90 сек)                │
│    - Извлечение аудио (FFmpeg)                           │
│    - Определение битов (librosa)                         │
│    - Извлечение поз из всех кадров (MediaPipe)          │
│    - Определение шагов по движению стоп                  │
│    - Сопоставление шагов с битами                        │
│    → rhythm_errors: [{timestamp, description, ...}]      │
│                                                           │
│  ШАГ 2: Извлечение 100 ключевых кадров (~5 сек)         │
│    - Равномерное распределение по длительности           │
│    - Конвертация в JPEG bytes                            │
│                                                           │
│  ШАГ 3: Claude API (~30-60 сек)                          │
│    - Отправка 100 кадров + данные о ритме                │
│    - Анализ: постура, техника, музыкальность             │
│    - Распознавание элементов (Американка, Солнышко, etc) │
│    → claude_errors: [{timestamp, category, ...}]         │
│                                                           │
│  ШАГ 4: Объединение ошибок                               │
│    all_errors = rhythm_errors + claude_errors            │
│                                                           │
│  ШАГ 5: Отбор топ-10 по severity                         │
│    - Сортировка: critical > high > medium > low          │
│    - Берём первые 10                                     │
│                                                           │
│  ШАГ 6: Генерация скриншотов (~30-60 сек)               │
│    - Для каждой ошибки:                                  │
│      * Извлечь кадр по timestamp (FFmpeg)                │
│      * Нарисовать красный скелет (текущая поза)          │
│      * Получить эталонную позу (если элемент распознан)  │
│      * Нарисовать зелёный скелет (правильная поза)       │
│      * Нарисовать стрелки между точками                  │
│      * Добавить текст снизу                              │
│      * Сохранить композитный скриншот                    │
│                                                           │
│  ШАГ 7: Сохранение результатов в БД                      │
│    - Analysis: оценки, статус = "completed"              │
│    - Errors: топ-10 с путями к скриншотам                │
└──────────────────┬───────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────┐
│ 3. ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ (Frontend)                    │
│    - Видеоплеер с исходным видео                         │
│    - Список ошибок с категориями                         │
│    - Скриншоты с красным/зелёным скелетом                │
│    - Описание + рекомендация для каждой ошибки           │
│    - Кнопки: Сохранить / Не сохранять                    │
└──────────────────────────────────────────────────────────┘
```

### 3.2. Время обработки (2-минутное видео)

| Этап | Время |
|------|-------|
| Извлечение аудио | 5 сек |
| Анализ ритма (librosa) | 15 сек |
| MediaPipe на всех кадрах | 75 сек |
| Извлечение 100 кадров | 5 сек |
| Claude API | 45 сек |
| Генерация 10 скриншотов | 45 сек |
| **ИТОГО** | **190 сек ≈ 3 минуты** |

*Для 10-минутного видео: ~10-15 минут*

---

## 4. Схема базы данных

### 4.1. ER-диаграмма

```
┌─────────────────┐
│     Users       │
├─────────────────┤
│ id              │◄──┐
│ email           │   │
│ password_hash   │   │
│ name            │   │
│ avatar_url      │   │
│ created_at      │   │
│ updated_at      │   │
└─────────────────┘   │
                      │
┌─────────────────┐   │
│  TempUploads    │   │
├─────────────────┤   │
│ id              │   │
│ user_id         │───┘
│ file_path       │
│ uploaded_at     │
│ expires_at      │
└─────────────────┘

┌─────────────────┐
│     Videos      │
├─────────────────┤
│ id              │◄──┐
│ user_id         │───┤
│ original_filename│   │
│ file_path       │   │
│ thumbnail_path  │   │
│ duration        │   │
│ size            │   │
│ resolution      │   │
│ fps             │   │
│ format          │   │
│ uploaded_at     │   │
│ is_saved        │   │
└─────────────────┘   │
                      │
┌─────────────────┐   │
│   Analyses      │   │
├─────────────────┤   │
│ id              │◄──┼──┐
│ video_id        │───┘  │
│ status          │      │
│ overall_score   │      │
│ rhythm_score    │      │
│ posture_score   │      │
│ technique_score │      │
│ musicality_score│      │
│ total_errors    │      │
│ ai_response     │      │
│ processing_time │      │
│ created_at      │      │
│ completed_at    │      │
│ error_message   │      │
└─────────────────┘      │
                         │
┌─────────────────┐      │
│     Errors      │      │
├─────────────────┤      │
│ id              │      │
│ analysis_id     │──────┘
│ timestamp       │
│ category        │
│ severity        │
│ title           │
│ description     │
│ recommendation  │
│ screenshot_path │
│ detected_element│
│ created_at      │
└─────────────────┘
```

### 4.2. Ключевые таблицы

**Users**
- Аутентификация и профиль пользователя
- Связь 1:N с Videos и TempUploads

**Videos**
- Хранит метаданные загруженного видео
- `is_saved` = False → временное (можно удалить)
- `is_saved` = True → сохранённое пользователем

**TempUploads**
- Временные файлы с автоматическим удалением
- `expires_at` - время истечения (24 часа после загрузки)
- Celery задача каждый час удаляет истёкшие

**Analyses**
- Результат анализа одного видео
- `status`: queued → processing → completed / failed
- Оценки по 4 категориям + общая

**Errors**
- Конкретные ошибки (топ-10)
- `category`: rhythm, posture, technique, musicality
- `severity`: critical, high, medium, low
- `screenshot_path` - путь к композитному скриншоту

---

## 5. API Endpoints

### 5.1. Authentication

```
POST /api/auth/register
Body: { email, password, name? }
Response: { id, email, name, created_at }

POST /api/auth/login
Body: { email, password }
Response: { access_token, token_type }

GET /api/users/me
Headers: Authorization: Bearer <token>
Response: { id, email, name, avatar_url, created_at }

PUT /api/users/me
Headers: Authorization: Bearer <token>
Body: { name?, avatar_url? }
Response: { id, email, name, avatar_url, created_at }
```

### 5.2. Video Upload & Analysis

```
POST /api/videos/upload
Headers: Authorization: Bearer <token>
Body: multipart/form-data (file)
Response: { video_id, analysis_id, status: "queued" }

GET /api/videos/analysis/{analysis_id}
Headers: Authorization: Bearer <token>
Response: {
  id, video_id, status,
  overall_score, rhythm_score, posture_score, technique_score, musicality_score,
  total_errors, processing_time,
  errors: [
    {
      id, timestamp, category, severity,
      title, description, recommendation,
      screenshot_path, detected_element
    }
  ]
}

POST /api/videos/analyses/{analysis_id}/save
Headers: Authorization: Bearer <token>
Response: { status: "saved", video_id }
Description: Переносит видео из temp/ в saved/, устанавливает is_saved=True

DELETE /api/videos/analyses/{analysis_id}
Headers: Authorization: Bearer <token>
Response: { status: "deleted" }
Description: Удаляет видео, скриншоты и все записи из БД

GET /api/videos/history?limit=20&offset=0
Headers: Authorization: Bearer <token>
Response: {
  videos: [
    {
      id, original_filename, duration, uploaded_at, thumbnail_path,
      analysis: { id, overall_score, total_errors }
    }
  ],
  total
}
```

---

## 6. Сервисы (Services Layer)

### 6.1. AudioService
**Назначение:** Анализ аудио и определение битов

**Методы:**
```python
analyze_audio(audio_path: str) -> Dict
  # → { tempo, beats: [timestamps], duration, sample_rate }

find_closest_beat(timestamp: float, beats: List[float]) -> Tuple[float, float]
  # → (closest_beat_time, difference)

is_on_beat(timestamp: float, beats: List[float], tolerance: float = 0.15) -> bool
```

### 6.2. PoseService
**Назначение:** Определение поз через MediaPipe

**Методы:**
```python
extract_poses_from_video(video_path: str) -> List[Dict]
  # → [{ frame, timestamp, landmarks: [33 точки], detected: bool }]

detect_steps(poses: List[Dict]) -> List[Dict]
  # → [{ timestamp, foot: 'left'|'right', type: 'step' }]

calculate_angles(landmarks: List[Dict]) -> Dict
  # → { spine_angle, left_knee_angle, right_knee_angle }
```

### 6.3. RhythmService
**Назначение:** Локальный анализ ритма

**Методы:**
```python
analyze_rhythm(video_path: str) -> Dict
  # 1. Извлекает аудио
  # 2. Определяет биты (librosa)
  # 3. Извлекает позы (MediaPipe)
  # 4. Определяет шаги
  # 5. Сопоставляет шаги с битами
  # → { tempo, total_beats, total_steps, accuracy, errors: [], rhythm_score }
```

### 6.4. ClaudeService
**Назначение:** Интеграция с Claude Opus 5.5

**Методы:**
```python
analyze_video(frames: List[bytes], rhythm_errors: List[Dict]) -> Dict
  # Отправляет 100 кадров + данные о ритме в Claude
  # → { posture_score, technique_score, musicality_score, errors: [] }
```

### 6.5. ReferenceService
**Назначение:** Работа с эталонными позами

**Методы:**
```python
get_reference(element_name: str) -> Optional[Dict]
  # Загружает JSON с эталонными позами элемента
  # → { element, total_frames, fps, poses: [] }

find_similar_pose(element_name: str, target_timestamp: float) -> Optional[Dict]
  # Находит наиболее похожую позу из эталона

list_available_elements() -> List[str]
  # → ['Американка', 'Солнышко', ...]
```

### 6.6. VisualizationService
**Назначение:** Генерация скриншотов с разметкой

**Методы:**
```python
create_error_screenshot(
    video_path: str,
    timestamp: float,
    error_data: Dict,
    detected_element: Optional[str]
) -> str
  # 1. Извлекает кадр
  # 2. Рисует красный скелет (MediaPipe на этом кадре)
  # 3. Получает эталонную позу (если элемент распознан)
  # 4. Рисует зелёный скелет
  # 5. Рисует стрелки
  # 6. Добавляет текст
  # → путь к сохранённому скриншоту
```

---

## 7. Промпт для Claude

### 7.1. Структура промпта

```
Проанализируй видео танца хастл по 100 ключевым кадрам.

ВАЖНО: Локальный анализ уже нашёл ошибки ритма (см. ниже).
Учитывай их при анализе постуры и техники.

ОШИБКИ РИТМА:
- 5.3s: Шаг left ногой опоздал на 0.27 сек
- 8.8s: Шаг right ногой опередил бит на 0.18 сек
...

ТВОЯ ЗАДАЧА:

1. ПОСТУРА
   - Ровная ли спина (10-20°)
   - Положение плеч (не зажаты)
   - Положение головы (смотрит вперёд)
   - Корпус не наклонён

2. ТЕХНИКА
   - Распознай элементы: Американка, Солнышко, Катапульта, Йoyo, etc
   - Правильность выполнения
   - Координация рук и ног

3. МУЗЫКАЛЬНОСТЬ
   - Соответствие движений характеру музыки
   - Акценты на смену фраз
   - Динамика

4. КОНТЕКСТ
   - Если на тех же таймкодах, где сбился ритм, есть ошибки постуры,
     укажи возможную связь

ФОРМАТ ОТВЕТА (строго JSON):
{
  "posture_score": 7.5,
  "technique_score": 6.8,
  "musicality_score": 8.0,
  "errors": [
    {
      "timestamp": 8.3,
      "category": "posture",
      "severity": "high",
      "detected_element": "Американка",
      "title": "Наклон корпуса вперёд",
      "description": "Корпус наклонён на 30-35°. Норма: 10-20°.",
      "recommendation": "Выпрями спину, подтяни живот."
    }
  ]
}

severity: critical > high > medium > low
```

---

## 8. Распознавание элементов (Гибрид)

### 8.1. Подход

**Шаг 1: Claude пытается распознать**
- Получает 100 кадров
- Анализирует визуально
- Возвращает `detected_element` для каждой ошибки

**Шаг 2: MediaPipe правила (подстраховка)**
Для явных случаев:

```python
def detect_element_simple(poses: List[Dict], timestamp: float) -> Optional[str]:
    # Американка: руки обоих подняты выше головы
    if all_hands_up(poses):
        return "Американка"
    
    # Солнышко: вращение > 270° за 1-2 секунды
    if rotation_detected(poses, min_angle=270):
        return "Солнышко"
    
    return None
```

### 8.2. Приоритет
1. Если Claude распознал → используем его
2. Если Claude не распознал → проверяем через MediaPipe правила
3. Если оба не распознали → `detected_element = null`

---

## 9. Frontend: Структура компонентов

```
src/
├── pages/
│   ├── LoginPage.tsx
│   ├── RegisterPage.tsx
│   ├── UploadPage.tsx
│   ├── ProcessingPage.tsx
│   ├── ResultsPage.tsx
│   ├── ProfilePage.tsx
│   └── VideoHistoryPage.tsx
│
├── components/
│   ├── VideoUploader.tsx      # Drag & drop, валидация
│   ├── ProcessingProgress.tsx # Прогресс-бар с этапами
│   ├── VideoPlayer.tsx        # Плеер + timeline с ошибками
│   ├── ErrorCard.tsx          # Карточка одной ошибки
│   ├── ErrorsList.tsx         # Список всех ошибок
│   ├── ScoresSummary.tsx      # Оценки по категориям
│   ├── ProgressChart.tsx      # График прогресса (recharts)
│   └── Header.tsx             # Навигация
│
├── services/
│   ├── api.ts                 # Axios instance
│   ├── authService.ts         # register, login, getMe
│   └── videoService.ts        # upload, getAnalysis, save, discard
│
├── hooks/
│   ├── useAuth.tsx            # Auth context
│   └── usePolling.tsx         # Polling статуса анализа
│
├── types/
│   └── index.ts               # TypeScript interfaces
│
└── utils/
    └── formatters.ts          # Форматирование времени, оценок
```

---

## 10. Celery: Архитектура задач

### 10.1. Задачи

```
app/tasks/
├── video_tasks.py
│   └── process_video_task(video_id, video_path)
│       - Основная задача обработки видео
│       - 7 шагов (см. раздел 3.1)
│
└── cleanup_tasks.py
    └── cleanup_expired_uploads()
        - Периодическая задача (каждый час)
        - Удаляет истёкшие TempUploads
```

### 10.2. Celery Beat Schedule

```python
celery_app.conf.beat_schedule = {
    'cleanup-expired-uploads': {
        'task': 'app.tasks.cleanup_tasks.cleanup_expired_uploads',
        'schedule': crontab(minute=0),  # Каждый час
    },
}
```

### 10.3. Запуск

```bash
# Worker (обрабатывает задачи)
celery -A app.core.celery_app worker --loglevel=info

# Beat (планировщик периодических задач)
celery -A app.core.celery_app beat --loglevel=info
```

---

## 11. Безопасность

### 11.1. Аутентификация
- JWT токены (access token)
- Хеширование паролей (bcrypt)
- Срок действия токена: 60 минут

### 11.2. Авторизация
- Каждый endpoint проверяет токен
- Пользователь может видеть только свои видео
- Middleware для проверки прав доступа

### 11.3. Валидация
- Формат видео: MP4, AVI, MOV
- Размер: ≤ 1 GB
- Длительность: ≤ 10 минут
- Проверка на серверной стороне

### 11.4. Файлы
- Временные файлы удаляются через 24 часа
- Каждый файл привязан к пользователю
- UUID в именах файлов (предотвращение коллизий)

---

## 12. Масштабирование (будущее)

### 12.1. Текущие ограничения MVP
- 1 Celery worker (последовательная обработка видео)
- Локальное хранение файлов
- Без кеширования результатов

### 12.2. Пути масштабирования

**Горизонтальное:**
- Несколько Celery workers (параллельная обработка)
- Load balancer для FastAPI
- Shared storage (S3, MinIO)

**Вертикальное:**
- GPU для MediaPipe (4x быстрее)
- Больше RAM для Celery workers
- SSD для быстрого I/O

**Оптимизация:**
- Параллелизация (аудио + видео одновременно)
- Кеширование эталонных поз в Redis
- CDN для статики

---

## 13. Стоимость обработки

### 13.1. Claude Opus 5.5 Pricing (примерно)

**Для 2-минутного видео:**
- 100 кадров JPEG (~200 KB каждый) = 20 MB
- Промпт: ~2000 токенов
- Ответ: ~1500 токенов

**Примерная стоимость:** $2-3 за видео

**Оптимизация:**
- Уменьшить размер кадров (640x480 вместо 1920x1080)
- Сжатие JPEG (quality=80)
- → ~$1.5-2 за видео

### 13.2. Инфраструктура
- PostgreSQL + Redis (Docker): бесплатно локально
- Сервер (VPS): $5-20/месяц
- Домен: $10/год

**Итого для MVP:** ~$2 за анализ + инфраструктура

---

## 14. Мониторинг и логирование

### 14.1. Логи
```python
import logging

logger = logging.getLogger(__name__)

@celery_app.task
def process_video_task(video_id, video_path):
    logger.info(f"Starting analysis for video_id={video_id}")
    # ...
    logger.info(f"Completed in {processing_time}s")
```

### 14.2. Метрики (будущее)
- Количество обработанных видео
- Среднее время обработки
- Ошибки AI API
- Использование диска

---

## 15. Тестирование

### 15.1. Unit тесты
- Сервисы (AudioService, PoseService, etc)
- API endpoints
- Утилиты (VideoUtils, FrameExtractor)

### 15.2. Integration тесты
- Celery задача end-to-end
- API → БД → Response

### 15.3. E2E тесты
- Frontend: загрузка → обработка → результат
- Проверка UI flow

---

## 16. Развертывание

### 16.1. Локальная разработка
```bash
# Backend
docker-compose up -d
cd backend
alembic upgrade head
python -m app.main

# Celery
celery -A app.core.celery_app worker --loglevel=info
celery -A app.core.celery_app beat --loglevel=info

# Frontend
cd frontend
npm run dev
```

### 16.2. Production (будущее)
- Docker Compose production config
- Nginx для статики
- Gunicorn для FastAPI
- SSL сертификат (Let's Encrypt)

---

## 17. План разработки

**Детальный план:** См. `FULL_MVP_PLAN.md`

**Краткая сводка:**
- Неделя 1: Подготовка, Auth, датасет
- Неделя 2: Анализ ритма (локально)
- Неделя 3: Claude API + визуализация
- Неделя 4: Интеграция в Celery
- Недели 5-7: Frontend
- Неделя 8: Личный кабинет
- Недели 9-10: Полировка + тесты
- Недели 11-12: Документация + презентация
- Неделя 13: Резерв + защита

**Общий срок:** 12-13 недель

---

## 18. Риски и митигации

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Claude API дорого | Средняя | Высокое | Сжатие изображений, оптимизация промпта |
| Медленная обработка | Средняя | Среднее | Прогресс-бар, можно закрыть вкладку |
| Плохое качество анализа | Низкая | Высокое | Тестирование на разных видео, итерация промпта |
| MediaPipe не определяет позу | Низкая | Среднее | Fallback сообщение, требовать хорошее освещение |
| Нехватка времени | Высокая | Высокое | Приоритизация MVP, отказ от бэклога |
| Claude API недоступен | Низкая | Критичное | Retry логика, fallback на локальный анализ |

---

## 19. Бэклог (после MVP)

### Функциональные улучшения:
- Email-уведомления после обработки
- Сравнение с предыдущими анализами (прогресс)
- Экспорт отчётов (PDF)
- Анализ взаимодействия партнеров (парные танцы)
- Видео с разметкой (наложение скелета на видео)

### Технические улучшения:
- Оптимизация скорости (параллелизация)
- GPU ускорение MediaPipe
- Кеширование эталонных поз в Redis
- S3 для хранения файлов
- WebSocket для real-time прогресса

---

*Документ обновлён: 11 октября 2026*
*Статус: Готов к разработке*

## 1. Общая схема системы

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│                      (React + TS)                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Auth    │  │  Upload  │  │  Results │  │ Profile  │   │
│  │  Pages   │  │  Page    │  │  Page    │  │  Page    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP REST API
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND API                              │
│                    (FastAPI + Python)                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                 API Routes                            │  │
│  │  /auth  /videos  /analyses  /users  /reference       │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Business Logic Layer                     │  │
│  │  - Auth Service                                       │  │
│  │  - Video Service                                      │  │
│  │  - Analysis Service                                   │  │
│  └──────────────────────────────────────────────────────┘  │
└──────┬────────────┬────────────┬────────────┬──────────────┘
       │            │            │            │
       ▼            ▼            ▼            ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐
│PostgreSQL│ │  Redis   │ │  Celery  │ │ File Storage│
│    DB    │ │  Cache   │ │  Workers │ │   (local)   │
└──────────┘ └──────────┘ └──────────┘ └─────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
            ┌──────────────┐      ┌──────────────┐
            │  MediaPipe   │      │    Gemini    │
            │   (local)    │      │  2.0 Flash   │
            │              │      │   API        │
            │ - Pose       │      │              │
            │ - Skeleton   │      │ - Video      │
            │              │      │   Analysis   │
            └──────────────┘      └──────────────┘
                    │
                    ▼
            ┌──────────────┐
            │   OpenCV     │
            │              │
            │ - Frames     │
            │ - Drawing    │
            │ - Overlay    │
            └──────────────┘
```

---

## 2. Детальная архитектура Backend

### 2.1. Структура проекта

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Конфигурация (env vars)
│   │
│   ├── api/                    # API endpoints
│   │   ├── __init__.py
│   │   ├── deps.py             # Зависимости (auth, db)
│   │   ├── auth.py             # /auth/register, /auth/login
│   │   ├── videos.py           # /videos/upload, /videos/{id}
│   │   ├── analyses.py         # /analyses/{id}, /analyses/{id}/save
│   │   └── users.py            # /users/me, /users/profile
│   │
│   ├── services/               # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── auth_service.py     # Регистрация, авторизация
│   │   ├── video_service.py    # Загрузка, валидация видео
│   │   ├── analysis_service.py # Оркестрация анализа
│   │   ├── ai_service.py       # Взаимодействие с Gemini API
│   │   ├── pose_service.py     # MediaPipe pose estimation
│   │   ├── visualization_service.py # Создание скриншотов с разметкой
│   │   └── reference_service.py # Работа с эталонными позами
│   │
│   ├── models/                 # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── video.py
│   │   ├── analysis.py
│   │   ├── error.py
│   │   └── temp_upload.py
│   │
│   ├── schemas/                # Pydantic schemas (API contracts)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── video.py
│   │   ├── analysis.py
│   │   └── error.py
│   │
│   ├── tasks/                  # Celery tasks
│   │   ├── __init__.py
│   │   ├── video_tasks.py      # Фоновая обработка видео
│   │   └── cleanup_tasks.py    # Очистка временных файлов
│   │
│   ├── db/                     # База данных
│   │   ├── __init__.py
│   │   ├── session.py          # Подключение к БД
│   │   └── migrations/         # Alembic migrations
│   │
│   ├── core/                   # Ядро
│   │   ├── __init__.py
│   │   ├── security.py         # Хеширование паролей, JWT
│   │   └── exceptions.py       # Кастомные исключения
│   │
│   └── utils/                  # Утилиты
│       ├── __init__.py
│       ├── video_utils.py      # FFmpeg обёртки
│       ├── file_utils.py       # Работа с файлами
│       └── validators.py       # Валидация данных
│
├── data/                       # Данные
│   ├── reference_poses.json    # Эталонные позы из датасета
│   └── uploads/                # Загруженные видео
│       ├── temp/               # Временные файлы
│       └── saved/              # Сохранённые видео
│
├── tests/                      # Тесты
│   ├── test_api/
│   ├── test_services/
│   └── test_tasks/
│
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## 3. Компоненты Backend

### 3.1. FastAPI Application (main.py)

**Ответственность:**
- HTTP сервер
- Роутинг запросов
- CORS настройки
- Обработка ошибок
- Middleware (логирование, аутентификация)

**Технологии:**
- FastAPI 0.115+
- Uvicorn (ASGI сервер)
- Python 3.10+

---

### 3.2. API Routes

#### `/auth` — Авторизация
```python
POST /auth/register
  Body: { email, password, name }
  Response: { user_id, token }

POST /auth/login
  Body: { email, password }
  Response: { token, user }

POST /auth/logout
  Headers: Authorization: Bearer {token}
  Response: { success: true }
```

#### `/videos` — Видео
```python
POST /videos/upload
  Headers: Authorization: Bearer {token}
  Body: multipart/form-data (video file)
  Response: { video_id, upload_status, analysis_job_id }

GET /videos/{video_id}
  Response: { video_id, file_url, duration, size, ... }

DELETE /videos/{video_id}
  Response: { success: true }
```

#### `/analyses` — Анализы
```python
GET /analyses/{analysis_id}
  Response: { analysis_id, status, scores, errors[], ... }

POST /analyses/{analysis_id}/save
  Body: { save: true/false }
  Response: { success: true, video_id? }

GET /analyses/{analysis_id}/screenshots
  Response: [ { timestamp, screenshot_url, error_id }, ... ]
```

#### `/users` — Пользователи
```python
GET /users/me
  Response: { user_id, email, name, avatar_url, ... }

PUT /users/profile
  Body: { name?, avatar? }
  Response: { user }

GET /users/history
  Response: { videos: [...], stats: {...} }
```

---

### 3.3. Services (Бизнес-логика)

#### **AuthService**
```python
class AuthService:
    def register(email, password, name) -> User
    def login(email, password) -> (User, token)
    def verify_token(token) -> User
    def hash_password(password) -> str
    def verify_password(password, hash) -> bool
```

#### **VideoService**
```python
class VideoService:
    def upload_video(file, user_id) -> TempUpload
    def validate_video(file) -> ValidationResult
        # Проверка формата, размера, длительности
    def extract_metadata(file_path) -> VideoMetadata
        # FFmpeg: duration, resolution, fps, codec
    def create_thumbnail(file_path) -> thumbnail_path
```

#### **AnalysisService** (Оркестратор)
```python
class AnalysisService:
    def start_analysis(video_id, user_id) -> Analysis
        # Создаёт запись Analysis со статусом "queued"
        # Запускает Celery task
        
    def process_video(analysis_id) -> Analysis
        # 1. Отправляет видео в Gemini API
        # 2. Получает JSON с ошибками
        # 3. Извлекает кадры по таймкодам
        # 4. Создаёт скриншоты с разметкой
        # 5. Сохраняет результаты в БД
        
    def save_analysis(analysis_id, user_id) -> Video
        # Переносит из TempUploads в Videos
        # Устанавливает is_saved = True
```

#### **AIService** (Gemini API)
```python
class AIService:
    def analyze_video(video_path) -> AIAnalysisResult
        # Отправляет видео в Gemini 2.0 Flash
        # Возвращает структурированный JSON
        
    def format_prompt() -> str
        # Промпт для Gemini (из test_ai_prompt.md)
```

**Формат ответа от Gemini:**
```python
@dataclass
class AIAnalysisResult:
    overall_score: float
    scores: CategoryScores  # rhythm, posture, technique, musicality
    errors: List[ErrorData]
    summary: str

@dataclass
class ErrorData:
    timestamp: float
    category: str
    severity: str
    description: str
    recommendation: str
    detected_element: Optional[str]
```

#### **PoseService** (MediaPipe)
```python
class PoseService:
    def extract_pose(frame) -> PoseLandmarks
        # MediaPipe Pose: 33 ключевые точки
        
    def calculate_angles(landmarks) -> Dict[str, float]
        # Углы суставов, наклон корпуса, etc
        
    def correct_pose(current_pose, reference_pose) -> CorrectedPose
        # Вычисляет "правильную" позу на основе эталона
```

#### **VisualizationService** (OpenCV)
```python
class VisualizationService:
    def create_error_screenshot(
        video_path, 
        timestamp, 
        error_data,
        reference_pose
    ) -> screenshot_path
        # 1. Извлекает кадр по timestamp
        # 2. Определяет текущую позу (MediaPipe)
        # 3. Рисует красный скелет (текущая поза)
        # 4. Рисует зелёный скелет (правильная поза)
        # 5. Добавляет стрелки/подписи
        # 6. Сохраняет изображение
```

#### **ReferenceService** (Эталонные позы)
```python
class ReferenceService:
    def load_references() -> Dict[str, ReferencePose]
        # Загружает reference_poses.json
        
    def get_reference(element_name) -> ReferencePose
        # Возвращает эталон для элемента (Американка, Солнышко, etc)
        
    def build_references_from_dataset() -> None
        # Обрабатывает все видео из hasl_files/
        # Извлекает средние позы для каждого элемента
        # Сохраняет в reference_poses.json
```

---

### 3.4. Celery Tasks (Фоновая обработка)

#### **video_tasks.py**
```python
@celery.task
def process_video_task(analysis_id: int):
    """
    Фоновая задача обработки видео
    Время: 5-10 минут для 2-минутного видео
    """
    analysis = db.get(Analysis, analysis_id)
    
    try:
        # 1. Обновить статус
        analysis.status = "processing"
        db.commit()
        
        # 2. Отправить в Gemini API
        ai_result = ai_service.analyze_video(analysis.video.file_path)
        
        # 3. Сохранить базовые результаты
        analysis.overall_score = ai_result.overall_score
        analysis.rhythm_score = ai_result.scores.rhythm
        # ... другие оценки
        
        # 4. Создать записи ошибок
        for error_data in ai_result.errors:
            error = Error(
                analysis_id=analysis_id,
                timestamp=error_data.timestamp,
                category=error_data.category,
                severity=error_data.severity,
                description=error_data.description,
                recommendation=error_data.recommendation
            )
            db.add(error)
        
        # 5. Создать скриншоты с разметкой
        for error_data in ai_result.errors:
            reference = reference_service.get_reference(
                error_data.detected_element
            )
            
            screenshot_path = visualization_service.create_error_screenshot(
                video_path=analysis.video.file_path,
                timestamp=error_data.timestamp,
                error_data=error_data,
                reference_pose=reference
            )
            
            error.screenshot_path = screenshot_path
        
        # 6. Завершить
        analysis.status = "completed"
        analysis.completed_at = datetime.now()
        db.commit()
        
    except Exception as e:
        analysis.status = "failed"
        analysis.error_message = str(e)
        db.commit()
        raise
```

#### **cleanup_tasks.py**
```python
@celery.task
def cleanup_temp_files():
    """
    Периодическая очистка временных файлов
    Запускается раз в час
    """
    expired = db.query(TempUpload).filter(
        TempUpload.expires_at < datetime.now()
    ).all()
    
    for temp in expired:
        # Удалить файлы
        os.remove(temp.file_path)
        # Удалить запись из БД
        db.delete(temp)
    
    db.commit()
```

---

### 3.5. База данных (PostgreSQL)

**Схема:**

```sql
-- Users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    avatar_url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- TempUploads (временные файлы)
CREATE TABLE temp_uploads (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL
);

-- Videos (сохранённые видео)
CREATE TABLE videos (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    original_filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    thumbnail_path TEXT,
    duration FLOAT NOT NULL,
    size BIGINT NOT NULL,
    resolution VARCHAR(20),
    fps INTEGER,
    format VARCHAR(10),
    uploaded_at TIMESTAMP DEFAULT NOW(),
    is_saved BOOLEAN DEFAULT FALSE
);

-- Analyses
CREATE TABLE analyses (
    id SERIAL PRIMARY KEY,
    video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL, -- queued, processing, completed, failed
    overall_score FLOAT,
    rhythm_score FLOAT,
    posture_score FLOAT,
    technique_score FLOAT,
    musicality_score FLOAT,
    total_errors INTEGER DEFAULT 0,
    ai_response JSONB, -- полный ответ от Gemini
    processing_time INTEGER, -- секунды
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    error_message TEXT
);

-- Errors
CREATE TABLE errors (
    id SERIAL PRIMARY KEY,
    analysis_id INTEGER REFERENCES analyses(id) ON DELETE CASCADE,
    timestamp FLOAT NOT NULL,
    category VARCHAR(20) NOT NULL, -- rhythm, posture, technique, musicality
    severity VARCHAR(20) NOT NULL, -- critical, medium, low
    title VARCHAR(255),
    description TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    screenshot_path TEXT,
    reference_screenshot_path TEXT,
    detected_element VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_videos_user_id ON videos(user_id);
CREATE INDEX idx_videos_is_saved ON videos(is_saved);
CREATE INDEX idx_analyses_video_id ON analyses(video_id);
CREATE INDEX idx_analyses_status ON analyses(status);
CREATE INDEX idx_errors_analysis_id ON errors(analysis_id);
CREATE INDEX idx_errors_category ON errors(category);
CREATE INDEX idx_temp_uploads_expires_at ON temp_uploads(expires_at);
```

---

## 4. Frontend Architecture

### 4.1. Структура проекта

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── App.tsx
│   ├── index.tsx
│   │
│   ├── pages/              # Страницы
│   │   ├── HomePage.tsx
│   │   ├── LoginPage.tsx
│   │   ├── RegisterPage.tsx
│   │   ├── UploadPage.tsx
│   │   ├── ProcessingPage.tsx
│   │   ├── ResultsPage.tsx
│   │   └── ProfilePage.tsx
│   │
│   ├── components/         # Компоненты
│   │   ├── Auth/
│   │   │   ├── LoginForm.tsx
│   │   │   └── RegisterForm.tsx
│   │   ├── Upload/
│   │   │   ├── VideoUploader.tsx
│   │   │   └── UploadProgress.tsx
│   │   ├── Results/
│   │   │   ├── VideoPlayer.tsx
│   │   │   ├── ErrorCard.tsx
│   │   │   ├── ErrorsList.tsx
│   │   │   └── ScoresSummary.tsx
│   │   ├── Profile/
│   │   │   ├── ProfileInfo.tsx
│   │   │   ├── VideoHistory.tsx
│   │   │   └── ProgressChart.tsx
│   │   └── Common/
│   │       ├── Header.tsx
│   │       ├── Footer.tsx
│   │       └── Loader.tsx
│   │
│   ├── hooks/              # Custom hooks
│   │   ├── useAuth.ts
│   │   ├── useVideoUpload.ts
│   │   └── useAnalysis.ts
│   │
│   ├── services/           # API клиенты
│   │   ├── api.ts          # Axios instance
│   │   ├── authService.ts
│   │   ├── videoService.ts
│   │   └── analysisService.ts
│   │
│   ├── store/              # State management (Redux/Zustand)
│   │   ├── authSlice.ts
│   │   ├── videoSlice.ts
│   │   └── store.ts
│   │
│   ├── types/              # TypeScript types
│   │   ├── user.ts
│   │   ├── video.ts
│   │   └── analysis.ts
│   │
│   └── utils/
│       ├── formatters.ts
│       └── validators.ts
│
├── package.json
└── tsconfig.json
```

---

### 4.2. Ключевые компоненты

#### **VideoPlayer** (результаты)
```tsx
interface VideoPlayerProps {
  videoUrl: string;
  errors: Error[];
}

// Функциональность:
// - Воспроизведение видео
// - Клик по ошибке → перемотка на timestamp
// - Маркеры ошибок на timeline
```

#### **ErrorCard** (карточка ошибки)
```tsx
interface ErrorCardProps {
  error: {
    timestamp: number;
    category: string;
    severity: string;
    description: string;
    recommendation: string;
    screenshot_path: string;
  };
  onClick: () => void; // Перемотка видео
}

// Визуально:
// ┌─────────────────────────────┐
// │ [Screenshot]                │
// │                             │
// │ ⏱ 00:08.3 | Постура        │
// │ ❌ Наклон корпуса вперёд    │
// │ ✅ Держи спину прямо        │
// └─────────────────────────────┘
```

#### **ProgressChart** (статистика)
```tsx
// Библиотека: recharts / chart.js
// График оценок по категориям со временем
```

---

## 5. Поток данных (Data Flow)

### 5.1. Загрузка и анализ видео

```
┌─────────┐
│  USER   │
└────┬────┘
     │ 1. Загрузка видео
     ▼
┌─────────────────┐
│  UploadPage     │
│  (Frontend)     │
└────┬────────────┘
     │ 2. POST /videos/upload
     ▼
┌─────────────────┐
│  VideoService   │
│  (Backend)      │
│  - Validate     │
│  - Save to temp │
│  - Create       │
│    TempUpload   │
└────┬────────────┘
     │ 3. Start Celery task
     ▼
┌─────────────────┐
│ AnalysisService │
│  - Create       │
│    Analysis     │
│    (queued)     │
└────┬────────────┘
     │ 4. Return job_id
     ▼
┌─────────────────┐
│  ProcessingPage │
│  (Frontend)     │
│  - Show progress│
│  - Poll status  │
└────┬────────────┘
     │ 5. GET /analyses/{id} (polling)
     ▼
┌─────────────────┐
│ Celery Worker   │
│ (Background)    │
└────┬────────────┘
     │ 6. Send video to Gemini
     ▼
┌─────────────────┐
│  Gemini API     │
│  - Analyze      │
│  - Return JSON  │
└────┬────────────┘
     │ 7. Process results
     ▼
┌─────────────────┐
│  PoseService +  │
│  Visualization  │
│  - Extract pose │
│  - Draw overlay │
│  - Save screens │
└────┬────────────┘
     │ 8. Save to DB
     ▼
┌─────────────────┐
│  Analysis       │
│  (completed)    │
└────┬────────────┘
     │ 9. Frontend detects completion
     ▼
┌─────────────────┐
│  ResultsPage    │
│  - Show video   │
│  - Show errors  │
│  - Save/Discard │
└─────────────────┘
```

---

### 5.2. Сохранение результата

```
┌─────────┐
│  USER   │ Нажимает "Сохранить"
└────┬────┘
     │ POST /analyses/{id}/save
     ▼
┌─────────────────┐
│ AnalysisService │
│  - Move from    │
│    TempUploads  │
│    to Videos    │
│  - Set is_saved │
│    = true       │
└────┬────────────┘
     │ Persist in DB
     ▼
┌─────────────────┐
│  ProfilePage    │
│  - Show in      │
│    history      │
└─────────────────┘
```

---

## 6. Технологический стек (итоговый)

### Backend
| Компонент | Технология |
|-----------|------------|
| Framework | FastAPI 0.115+ |
| Runtime | Python 3.10+ |
| ASGI Server | Uvicorn |
| Database | PostgreSQL 15+ |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Cache | Redis 7+ |
| Task Queue | Celery 5+ |
| Auth | JWT (python-jose) |
| Password Hash | bcrypt |
| AI API | Google Gemini 2.0 Flash |
| Pose Estimation | MediaPipe 0.10+ |
| Video Processing | OpenCV 4.8+ |
| Audio Processing | FFmpeg |

### Frontend
| Компонент | Технология |
|-----------|------------|
| Framework | React 18+ |
| Language | TypeScript 5+ |
| Build Tool | Vite |
| UI Library | Material-UI (MUI) v6 |
| State | Redux Toolkit / Zustand |
| HTTP Client | Axios |
| Video Player | React Player |
| Charts | Recharts |
| Routing | React Router v6 |

### DevOps
| Компонент | Технология |
|-----------|------------|
| Containerization | Docker + Docker Compose |
| Reverse Proxy | Nginx (опционально) |
| Deployment | Local / VPS / Cloud |

---

## 7. API Endpoints (полный список)

### Authentication
```
POST   /api/auth/register      - Регистрация
POST   /api/auth/login         - Вход
POST   /api/auth/logout        - Выход
POST   /api/auth/refresh       - Обновление токена
```

### Videos
```
POST   /api/videos/upload      - Загрузка видео
GET    /api/videos/{id}        - Получить видео
DELETE /api/videos/{id}        - Удалить видео
GET    /api/videos/{id}/stream - Стрим видео
```

### Analyses
```
POST   /api/analyses/start     - Запустить анализ
GET    /api/analyses/{id}      - Статус/результат анализа
POST   /api/analyses/{id}/save - Сохранить результат
DELETE /api/analyses/{id}      - Отменить/удалить
GET    /api/analyses/{id}/screenshots - Получить все скриншоты
```

### Users
```
GET    /api/users/me           - Текущий пользователь
PUT    /api/users/me           - Обновить профиль
GET    /api/users/history      - История анализов
GET    /api/users/stats        - Статистика прогресса
POST   /api/users/avatar       - Загрузить аватар
```

### Reference (служебные)
```
GET    /api/reference/poses    - Эталонные позы
POST   /api/reference/rebuild  - Пересобрать эталоны
```

---

## 8. Безопасность

### 8.1. Аутентификация
- JWT токены (access + refresh)
- Access token: 15 минут
- Refresh token: 7 дней
- Хранение refresh в httpOnly cookies

### 8.2. Авторизация
- Middleware проверяет токен на каждом защищённом endpoint
- User ID извлекается из токена
- Доступ только к своим данным

### 8.3. Валидация
- Pydantic schemas для всех входных данных
- Проверка типов файлов (magic bytes, не только расширение)
- Лимиты размера файлов (1 GB)
- Лимиты длительности видео (10 минут)

### 8.4. Защита от атак
- Rate limiting (Redis + slowapi)
- CORS настройки
- SQL injection защита (ORM)
- XSS защита (React escaping)
- CSRF защита (SameSite cookies)

---

## 9. Производительность

### 9.1. Кеширование
- Redis кеш для частых запросов (профили, статистика)
- TTL: 5 минут для статики, 1 минута для динамики

### 9.2. Оптимизация БД
- Индексы на foreign keys
- Индексы на поля для поиска (user_id, status)
- Connection pooling

### 9.3. Асинхронность
- FastAPI асинхронные endpoints где возможно
- Celery для долгих операций
- WebSocket для real-time статуса (опционально)

---

## 10. Мониторинг и логирование

### 10.1. Логирование
```python
# Уровни логов
- DEBUG: детальная информация для отладки
- INFO: общие события (запуск задач, завершение)
- WARNING: предупреждения (долгая обработка)
- ERROR: ошибки обработки
- CRITICAL: системные ошибки

# Формат
{
  "timestamp": "2026-10-11T10:30:00Z",
  "level": "INFO",
  "service": "analysis_service",
  "message": "Video analysis completed",
  "analysis_id": 123,
  "processing_time": 180
}
```

### 10.2. Метрики
- Время обработки видео
- Количество ошибок AI API
- Загрузка CPU/RAM
- Размер очереди Celery

---

## 11. Развёртывание (Deployment)

### 11.1. Docker Compose (для разработки)

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/hustl_db
      - REDIS_URL=redis://redis:6379/0
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    volumes:
      - ./backend:/app
      - uploads:/app/data/uploads
    depends_on:
      - db
      - redis

  celery_worker:
    build: ./backend
    command: celery -A app.tasks worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/hustl_db
      - REDIS_URL=redis://redis:6379/0
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    volumes:
      - uploads:/app/data/uploads
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=hustl_db
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:8000
    volumes:
      - ./frontend:/app

volumes:
  postgres_data:
  uploads:
```

---

## 12. Этапы разработки

### Этап 1: Подготовка (неделя 1-2)
- [x] Анализ требований
- [ ] Настройка окружения
- [ ] Создание структуры проекта
- [ ] Настройка Docker
- [ ] Инициализация БД

### Этап 2: Backend Core (неделя 3-4)
- [ ] FastAPI приложение
- [ ] Модели БД + миграции
- [ ] Auth (регистрация, вход, JWT)
- [ ] API endpoints (базовые)

### Этап 3: Video Processing (неделя 5-6)
- [ ] Загрузка видео
- [ ] Интеграция FFmpeg
- [ ] Celery setup
- [ ] Базовая обработка видео

### Этап 4: AI Integration (неделя 7-8)
- [ ] Интеграция Gemini API
- [ ] Обработка ответов
- [ ] Создание эталонной базы поз
- [ ] MediaPipe интеграция

### Этап 5: Visualization (неделя 9-10)
- [ ] Извлечение кадров
- [ ] OpenCV разметка
- [ ] Генерация скриншотов
- [ ] Сохранение результатов

### Этап 6: Frontend (неделя 11-13)
- [ ] React setup
- [ ] Страницы (Auth, Upload, Results, Profile)
- [ ] Компоненты
- [ ] API интеграция
- [ ] State management

### Этап 7: Интеграция и тестирование (неделя 14-15)
- [ ] E2E тестирование
- [ ] Исправление багов
- [ ] Оптимизация производительности
- [ ] UX улучшения

### Этап 8: Документация и презентация (неделя 16)
- [ ] Техническая документация
- [ ] Презентация для защиты
- [ ] Демо-видео
- [ ] Финальная отладка

---

## 13. Риски и митигации

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Gemini API дорого | Средняя | Высокое | Кеширование результатов, оптимизация промпта |
| Медленная обработка | Высокая | Среднее | Celery очередь, статус-бар пользователю |
| Плохое качество анализа ритма | Средняя | Высокое | Тестирование на разных видео, доработка промпта |
| Нехватка времени | Высокая | Высокое | Приоритизация MVP функций, отказ от бэклога |

---

*Документ обновляется по мере разработки*
