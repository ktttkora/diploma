# 📝 ИНСТРУКЦИИ ПО ДОКУМЕНТИРОВАНИЮ ДЛЯ АГЕНТОВ

**Каждый агент ОБЯЗАН документировать свою работу!**

---

## 🎯 ДЛЯ ORCHESTRATOR

### После КАЖДОЙ завершённой задачи:

**1. Обновить CHECKLIST.md**

```markdown
Найти строку с задачей:
- [ ] 2.4. Создать модель User

Заменить на:
- [x] 2.4. Создать модель User
```

**2. Обновить PROGRESS.md**

Создай файл `PROGRESS.md` если его нет, добавь запись:

```markdown
# 📊 ПРОГРЕСС РАЗРАБОТКИ

## Завершённые задачи

### [Дата] - Неделя 1, День 2

#### ✅ 2.4. Создать модель User
- **Файл:** `backend/app/models/user.py`
- **Developer:** 1 итерация
- **Reviewer:** APPROVE
- **Время:** ~15 минут
- **Заметки:** Добавлены relationships с Videos и TempUploads

---
```

**3. Обновить статистику**

В конце `PROGRESS.md` поддерживай актуальную статистику:

```markdown
## 📈 Общая статистика

- Всего задач: 260
- Завершено: 4
- Прогресс: 1.5%
- Текущая неделя: 1
- Текущий день: 2

### По категориям
- Backend модели: 3/5
- Backend API: 0/12
- Frontend компоненты: 0/15
- Сервисы: 0/10
```

---

## 💻 ДЛЯ DEVELOPER

### После КАЖДОГО созданного файла:

**1. Добавить запись в DEVELOPMENT_LOG.md**

```markdown
# 📚 ЖУРНАЛ РАЗРАБОТКИ

## [Дата] - backend/app/models/user.py

### Создан файл
**Путь:** `backend/app/models/user.py`

### Что сделано
- Создана SQLAlchemy модель User
- Добавлены поля: id, email, password_hash, name, avatar_url, created_at, updated_at
- Настроены relationships: videos, temp_uploads
- Добавлены indexes на email

### Ключевые решения
- Использовал CASCADE для автоматического удаления связанных записей
- email сделан unique для предотвращения дубликатов
- Timestamps автоматически управляются через server_default

### Зависимости
- sqlalchemy
- app.db.session.Base

### Связанные файлы
- Будет использоваться в: `app/models/video.py`, `app/models/temp_upload.py`

---
```

**2. Обновить CODE_INDEX.md** (индекс кода)

```markdown
# 🗂️ ИНДЕКС КОДА

## Backend Models

### user.py
- **Путь:** `backend/app/models/user.py`
- **Тип:** SQLAlchemy модель
- **Класс:** `User`
- **Relationships:** `videos`, `temp_uploads`
- **Создан:** [дата]
- **Статус:** ✅ Завершён

### video.py
- **Путь:** `backend/app/models/video.py`
- **Статус:** ⏳ В разработке

---

## Backend Services

### audio_service.py
- **Статус:** 📋 Запланирован

---
```

**3. Обновить API_REFERENCE.md** (если это API endpoint)

Если создал API endpoint, добавь в `API_REFERENCE.md`:

```markdown
# 📡 API REFERENCE

## Auth Endpoints

### POST /api/auth/register
**Создан:** [дата]
**Файл:** `backend/app/api/auth.py`

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "name": "User Name"
}
```

**Response:** 201 Created
```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "User Name",
  "created_at": "2026-10-11T10:00:00Z"
}
```

**Errors:**
- 400: Email already registered
- 422: Validation error

---
```

---

## 🔍 ДЛЯ REVIEWER

### После КАЖДОЙ проверки:

**1. Добавить запись в REVIEW_LOG.md**

```markdown
# 🔍 ЖУРНАЛ РЕВЬЮ

## [Дата] - backend/app/models/user.py

### Проверенный файл
**Путь:** `backend/app/models/user.py`
**Developer:** Claude
**Итерация:** 1

### Результат
**Вердикт:** ✅ APPROVE

### Что проверено
- ✅ Критические моменты: OK
- ✅ Type hints: Все добавлены
- ✅ Docstrings: Не требуются для моделей
- ✅ Naming: snake_case соблюдён
- ✅ Архитектура: Соответствует схеме БД

### Замечания
Нет замечаний. Код качественный.

### Рекомендации
В будущем можно добавить метод `to_dict()` для удобной сериализации.

---
```

**2. Обновить QUALITY_METRICS.md**

```markdown
# 📊 МЕТРИКИ КАЧЕСТВА

## Общая статистика

- Всего файлов проверено: 4
- APPROVE с первой итерации: 3 (75%)
- REQUEST_CHANGES: 1 (25%)
- Средняя итерация до APPROVE: 1.25

## По типам файлов

### Models (3 файла)
- APPROVE: 3
- REQUEST_CHANGES: 0
- Качество: 100%

### API Endpoints (1 файл)
- APPROVE: 0
- REQUEST_CHANGES: 1
- Основные проблемы: отсутствие type hints

---

## Частые проблемы

1. **Type hints** - 1 случай
2. **Docstrings** - 0 случаев
3. **Критические ошибки** - 0 случаев

---
```

---

## 📂 СТРУКТУРА ДОКУМЕНТАЦИИ

```
docs/
├── PROGRESS.md              # Orchestrator обновляет
├── DEVELOPMENT_LOG.md       # Developer обновляет
├── REVIEW_LOG.md            # Reviewer обновляет
├── CODE_INDEX.md            # Developer обновляет
├── API_REFERENCE.md         # Developer обновляет (для API)
├── QUALITY_METRICS.md       # Reviewer обновляет
└── DECISIONS.md             # Все агенты добавляют важные решения
```

---

## 🔄 WORKFLOW ДОКУМЕНТИРОВАНИЯ

### 1. Developer создал файл

```
1. Developer:
   ✅ Пишет код
   ✅ Добавляет запись в DEVELOPMENT_LOG.md
   ✅ Обновляет CODE_INDEX.md
   ✅ Обновляет API_REFERENCE.md (если API)
   → Отправляет Orchestrator

2. Orchestrator:
   ✅ Получает код
   → Отправляет Reviewer
```

### 2. Reviewer проверяет

```
3. Reviewer:
   ✅ Проверяет код
   ✅ Добавляет запись в REVIEW_LOG.md
   ✅ Обновляет QUALITY_METRICS.md
   → Отправляет вердикт Orchestrator
```

### 3. Orchestrator фиксирует

```
4. Orchestrator:
   ✅ Получает APPROVE
   ✅ Обновляет CHECKLIST.md: [ ] → [x]
   ✅ Добавляет запись в PROGRESS.md
   ✅ Обновляет статистику в PROGRESS.md
   → Переходит к следующей задаче
```

---

## 📋 ШАБЛОНЫ ДОКУМЕНТАЦИИ

### PROGRESS.md (Orchestrator)

```markdown
# 📊 ПРОГРЕСС РАЗРАБОТКИ

## Завершённые задачи

### [11.10.2026] - Неделя 1, День 2

#### ✅ 2.4. Создать модель User
- **Файл:** `backend/app/models/user.py`
- **Developer:** 1 итерация
- **Reviewer:** APPROVE
- **Время:** ~15 минут
- **Заметки:** -

#### ✅ 2.5. Создать модель Video
- **Файл:** `backend/app/models/video.py`
- **Developer:** 2 итерации
- **Reviewer:** APPROVE после исправления type hints
- **Время:** ~25 минут
- **Заметки:** Исправлены type hints для relationships

---

## 📈 Общая статистика

- Всего задач: 260
- Завершено: 5
- Прогресс: 1.9%
- Текущая неделя: 1
- Текущий день: 2

### По категориям
- Backend модели: 4/5 (80%)
- Backend API: 0/12 (0%)
- Frontend компоненты: 0/15 (0%)
- Сервисы: 0/10 (0%)

### По неделям
- Неделя 1: 5/44 задач (11%)
```

### DEVELOPMENT_LOG.md (Developer)

```markdown
# 📚 ЖУРНАЛ РАЗРАБОТКИ

## [11.10.2026 10:30] - backend/app/models/user.py

### Создан файл
**Путь:** `backend/app/models/user.py`
**Тип:** SQLAlchemy модель

### Что сделано
- Создана модель User
- Добавлены поля: id, email, password_hash, name, avatar_url
- Timestamps: created_at, updated_at
- Relationships: videos (1:N), temp_uploads (1:N)
- Indexes: email (unique)

### Ключевые решения
- CASCADE удаление для связанных записей
- server_default для timestamps
- email unique для предотвращения дубликатов

### Зависимости
- sqlalchemy 2.0.25

### Связанные файлы
- Используется в: auth.py, videos.py

---
```

### REVIEW_LOG.md (Reviewer)

```markdown
# 🔍 ЖУРНАЛ РЕВЬЮ

## [11.10.2026 10:45] - backend/app/models/user.py

### Файл
**Путь:** `backend/app/models/user.py`
**Итерация:** 1

### Результат
✅ **APPROVE**

### Проверка
- ✅ Критические моменты: OK
- ✅ Type hints: OK
- ✅ Naming: OK
- ✅ Архитектура: OK

### Замечания
Нет

---

## [11.10.2026 11:00] - backend/app/models/video.py

### Файл
**Путь:** `backend/app/models/video.py`
**Итерация:** 1

### Результат
⚠️ **REQUEST_CHANGES**

### Проблемы
1. Отсутствует type hint для relationship `user`
   - Где: строка 20
   - Исправление: добавить `user: User`

### Итерация 2
✅ **APPROVE** - проблема исправлена

---
```

### CODE_INDEX.md (Developer)

```markdown
# 🗂️ ИНДЕКС КОДА

## Backend

### Models (`backend/app/models/`)

| Файл | Класс | Статус | Создан | Связи |
|------|-------|--------|--------|-------|
| user.py | User | ✅ | 11.10 | videos, temp_uploads |
| video.py | Video | ✅ | 11.10 | user, analyses |
| analysis.py | Analysis | 📋 | - | - |

### API (`backend/app/api/`)

| Файл | Endpoints | Статус | Создан |
|------|-----------|--------|--------|
| auth.py | /register, /login | 📋 | - |
| users.py | /me | 📋 | - |

### Services (`backend/app/services/`)

| Файл | Класс | Статус | Создан |
|------|-------|--------|--------|
| audio_service.py | AudioService | 📋 | - |

## Frontend

### Pages (`frontend/src/pages/`)

| Файл | Компонент | Статус | Создан |
|------|-----------|--------|--------|
| LoginPage.tsx | LoginPage | 📋 | - |

---

**Легенда:**
- ✅ Завершён
- ⏳ В разработке
- 📋 Запланирован
```

---

## 🎯 ВАЖНО!

### Каждый агент ОБЯЗАН:

1. **Developer:**
   - ✅ Обновлять DEVELOPMENT_LOG.md после каждого файла
   - ✅ Обновлять CODE_INDEX.md

2. **Reviewer:**
   - ✅ Обновлять REVIEW_LOG.md после каждой проверки
   - ✅ Обновлять QUALITY_METRICS.md

3. **Orchestrator:**
   - ✅ Обновлять CHECKLIST.md после завершения задачи
   - ✅ Обновлять PROGRESS.md после каждой задачи

### Формат дат:
**[DD.MM.YYYY HH:MM]** - например: [11.10.2026 14:30]

### Статусы:
- ✅ Завершён
- ⏳ В разработке
- 📋 Запланирован
- ❌ Ошибка/отклонён

---

**Документация - это часть работы, не пропускайте её!**
