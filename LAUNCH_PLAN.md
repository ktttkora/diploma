# ⚙️ НАСТРОЙКИ ПРОЕКТА И ПЛАН ЗАПУСКА

**Дата:** 11 октября 2026  
**Статус:** Готов к запуску

---

## ✅ ПОДТВЕРЖДЁННЫЕ ДАННЫЕ

### Окружение
- **Claude Code:** Используется (Anthropic API подключен ✅)
- **ОС:** Windows
- **Docker:** Установлен (но не использовался ранее)
- **FFmpeg:** Будет установлен перед началом
- **Срок:** 16 недель (достаточно для 13-недельного плана + резерв)

### Пути
- **Датасет эталонов:** `C:\Users\kt\important\university\diploma\hasl_files`
- **Тестовые видео:** `C:\Users\kt\important\university\diploma\code\test`
- **Проект:** `C:\Users\kt\important\university\diploma\`

### Способ работы
- **3 агента через Claude Code** (вызов вручную по необходимости)
- **Файлы создаются:** через Claude Code напрямую
- **Коммиты:** делаешь ты вручную

---

## 🎯 СКОРРЕКТИРОВАННЫЙ ПЛАН ЗАПУСКА

### ДО НАЧАЛА РАЗРАБОТКИ (30 минут)

#### 1. Установить FFmpeg
```bash
# Windows: Скачать с https://www.gyan.dev/ffmpeg/builds/
# Добавить в PATH

# Проверка установки
ffmpeg -version
```

#### 2. Создать структуру папок
```bash
cd C:\Users\kt\important\university\diploma

mkdir backend
mkdir backend\app
mkdir backend\app\api
mkdir backend\app\models
mkdir backend\app\services
mkdir backend\app\tasks
mkdir backend\app\core
mkdir backend\app\db
mkdir backend\app\schemas
mkdir backend\app\utils
mkdir backend\data
mkdir backend\data\reference_poses
mkdir backend\data\uploads
mkdir backend\data\uploads\temp
mkdir backend\data\uploads\saved
mkdir backend\scripts
mkdir backend\tests

mkdir frontend
mkdir frontend\src
mkdir frontend\src\pages
mkdir frontend\src\components
mkdir frontend\src\services
mkdir frontend\src\hooks
mkdir frontend\src\types
mkdir frontend\src\utils
mkdir frontend\public

mkdir docs
```

#### 3. Создать файлы документации
```bash
cd docs

# Эти файлы уже созданы:
# CONTEXT.md
# ARCHITECTURE.md
# FULL_MVP_PLAN.md
# CHECKLIST.md
# AGENT_ROLES.md
# ORCHESTRATOR_PROMPT.md
# DEVELOPER_PROMPT.md
# REVIEWER_PROMPT.md
# DOCUMENTATION_GUIDE.md
# AUTONOMOUS_MODE.md
# README.md

# Нужно создать новые:
type nul > PROGRESS.md
type nul > DEVELOPMENT_LOG.md
type nul > REVIEW_LOG.md
type nul > CODE_INDEX.md
type nul > API_REFERENCE.md
type nul > QUALITY_METRICS.md
type nul > DECISIONS.md
```

#### 4. Инициализировать Git
```bash
cd C:\Users\kt\important\university\diploma

git init
git add .
git commit -m "Initial commit: project structure and documentation

- Added full documentation (CONTEXT, ARCHITECTURE, PLAN)
- Set up multi-agent system (ORCHESTRATOR, DEVELOPER, REVIEWER)
- Created project structure

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

#### 5. Проверить Docker
```bash
# Запустить Docker Desktop
# Проверить
docker --version
docker ps
```

#### 6. Обработать датасет (КРИТИЧНО!)

**Вариант A: Если датасет УЖЕ обработан в JSON**
- Проверь: есть ли файлы `backend/data/reference_poses/*.json`?
- Если есть → пропусти этот шаг

**Вариант B: Если датасет НЕ обработан (видео в hasl_files/)**
```bash
cd backend/scripts

# Создать скрипт extract_all_references.py (из FULL_MVP_PLAN.md День 1)
# Запустить (ЗАЙМЁТ 5-7 ЧАСОВ!)
python extract_all_references.py

# Можешь запустить на ночь и продолжить утром
```

---

## 🚀 ПОРЯДОК ЗАПУСКА АГЕНТОВ

### Способ 1: Через 3 отдельных чата Claude Code (РЕКОМЕНДУЮ)

**Шаг 1: Создать проект Claude Code**
```bash
# В Claude Code создай новый проект "Hustl Analyzer"
# Добавь в Project Knowledge:
- CONTEXT.md
- ARCHITECTURE.md
- FULL_MVP_PLAN.md
- CHECKLIST.md
- AGENT_ROLES.md
```

**Шаг 2: Открыть 3 чата**

**ЧАТ 1: ORCHESTRATOR**
```
Первое сообщение:

Ты Orchestrator в мультиагентной системе разработки проекта Hustl Analyzer.

Прочитай:
- ORCHESTRATOR_PROMPT.md
- AUTONOMOUS_MODE.md
- DOCUMENTATION_GUIDE.md

Режим работы: AUTONOMOUS

Твоя задача:
1. Читать FULL_MVP_PLAN.md
2. Брать задачи из CHECKLIST.md
3. Делегировать Developer
4. Получать код, отправлять Reviewer
5. Обновлять документацию
6. Спрашивать меня только при спорных вопросах

Готов начать работу?
```

**ЧАТ 2: DEVELOPER**
```
Ты Developer в мультиагентной системе.

Прочитай:
- DEVELOPER_PROMPT.md
- CONTEXT.md (ОБЯЗАТЕЛЬНО!)

Жди заданий от Orchestrator.

Готов к работе?
```

**ЧАТ 3: REVIEWER**
```
Ты Reviewer в мультиагентной системе.

Прочитай:
- REVIEWER_PROMPT.md
- CONTEXT.md (критические моменты!)

Жди кода на проверку от Orchestrator.

Готов к работе?
```

**Шаг 3: Запустить работу**

В чате ORCHESTRATOR:
```
Начинай работу с Неделя 1, День 1.

После каждой задачи сообщай мне:
- Что сделано
- Какие файлы созданы
- Нужно ли моё участие

При спорных вопросах останавливайся и спрашивай меня.

Начинай!
```

**Шаг 4: Workflow (как ты работаешь)**

```
1. Orchestrator в ЧАТ 1 выбирает задачу
2. Orchestrator пишет задание для Developer
3. ТЫ копируешь задание из ЧАТ 1 в ЧАТ 2 (Developer)
4. Developer пишет код
5. ТЫ копируешь код из ЧАТ 2 в ЧАТ 3 (Reviewer)
6. Reviewer проверяет
7. ТЫ копируешь результат из ЧАТ 3 в ЧАТ 1 (Orchestrator)
8. Если APPROVE:
   - Claude Code создаёт файл с кодом
   - Orchestrator обновляет CHECKLIST.md
   - Переход к следующей задаче
9. Если REQUEST_CHANGES:
   - Копируешь замечания в ЧАТ 2 (Developer)
   - Developer исправляет
   - Повтор с шага 5
```

---

### Способ 2: Один чат с режимами (ПРОЩЕ, НО МЕНЕЕ ЭФФЕКТИВНО)

**Единственный чат:**
```
Ты мультиагентная система разработки.

Режимы работы:
- Когда я пишу "ORCHESTRATOR:" - ты координатор
- Когда я пишу "DEVELOPER:" - ты разработчик
- Когда я пишу "REVIEWER:" - ты ревьюер

Прочитай все промпты:
- ORCHESTRATOR_PROMPT.md
- DEVELOPER_PROMPT.md
- REVIEWER_PROMPT.md
- CONTEXT.md
- AUTONOMOUS_MODE.md

Готов к работе?
```

**Затем работаешь так:**
```
Ты: ORCHESTRATOR: Начни с Неделя 1, День 1

Claude: [Orchestrator выбирает задачу и формирует задание для Developer]

Ты: DEVELOPER: [копируешь задание]

Claude: [Developer пишет код]

Ты: REVIEWER: [копируешь код]

Claude: [Reviewer проверяет]

Ты: ORCHESTRATOR: [копируешь вердикт]

Claude: [Orchestrator фиксирует или отправляет на доработку]
```

---

## 📋 CHECKLIST ПЕРЕД СТАРТОМ

- [ ] FFmpeg установлен и в PATH
- [ ] Docker Desktop запущен
- [ ] Структура папок создана
- [ ] Git инициализирован
- [ ] Датасет обработан (520 JSON файлов в reference_poses/)
- [ ] Тестовые видео доступны в code/test/
- [ ] Файлы документации созданы (PROGRESS.md, etc)
- [ ] Claude Code проект создан
- [ ] 3 чата открыты (или 1 для режима 2)
- [ ] Агенты проинструктированы

---

## 🎯 ПЕРВЫЙ ДЕНЬ РАБОТЫ (Неделя 1, День 1)

### План на день (8 задач, ~2-3 часа):

1. ✅ Создать Git репозиторий (УЖЕ СДЕЛАНО)
2. ✅ Создать .gitignore
3. ✅ Создать структуру папок (УЖЕ СДЕЛАНО)
4. ⏳ Написать скрипт extract_all_references.py
5. ⏳ Запустить обработку датасета (5-7 часов в фоне)
6. ✅ Установить Backend зависимости (requirements.txt)
7. ✅ Установить Frontend зависимости (package.json)
8. ✅ Запустить Docker Compose

### Ожидаемый результат:
- Все зависимости установлены
- PostgreSQL + Redis запущены в Docker
- Датасет обрабатывается в фоне
- Готовы к Дню 2 (Backend Core)

---

## 💡 РЕКОМЕНДАЦИИ

### Для эффективной работы:

1. **Работай блоками по 2-3 часа**
   - Запусти агентов на 2 часа
   - Они сделают 5-10 задач
   - Проверь результат
   - Сделай коммит
   - Перерыв

2. **Документация автоматически**
   - Агенты сами обновляют PROGRESS.md и логи
   - Ты только проверяешь

3. **Коммиты регулярно**
   - После каждого дня разработки
   - Или после каждых 10 файлов

4. **Спорные вопросы**
   - Агенты остановятся и спросят
   - Ты отвечаешь
   - Они продолжают

5. **Тестирование**
   - После каждой недели запускай систему
   - Проверяй что работает
   - Исправляй критичное

### График на 16 недель:

```
Недели 1-4: Ядро MVP (Backend + основной анализ)
Недели 5-8: Frontend + интеграция
Недели 9-10: Полировка + тесты
Неделя 11: Документация
Неделя 12: Презентация
Недели 13-14: Резерв (доработки, баги)
Недели 15-16: Финальная подготовка к защите
```

**У тебя 3 недели резерва - это отлично!**

---

## 🚨 КРИТИЧНЫЕ МОМЕНТЫ

### Если что-то сломалось:

1. **Docker не запускается**
   - Включи Hyper-V в Windows
   - Перезагрузи компьютер
   - Запусти Docker Desktop

2. **FFmpeg не найден**
   - Добавь в PATH вручную
   - Перезапусти терминал

3. **Claude API лимит**
   - Подожди час (лимиты восстанавливаются)
   - Продолжи работу

4. **Датасет не обрабатывается**
   - Проверь путь к видео
   - Убедись что MediaPipe установлен
   - Запусти скрипт заново

5. **Агенты зациклились**
   - Остановись
   - Перечитай CONTEXT.md
   - Перезапусти задачу

---

## ✅ ТЫ ГОТОВА НАЧАТЬ!

**Следующий шаг:**
1. Выполни checklist выше
2. Скажи мне: "Готова запустить агентов"
3. Я дам команду для Orchestrator
4. Начнётся разработка!

**Вопросы есть?**

---

*Сохрани этот файл - это твоя шпаргалка запуска.*
