# 🔍 ОБЗОР ПЛАНА: НАЙДЕННЫЕ ПРОБЛЕМЫ И ИСПРАВЛЕНИЯ

## Дата: 11 октября 2026
## Статус: Критический анализ архитектуры

---

## ❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ

### 1. **Генерация скриншотов отсутствует в Celery задаче**

**Проблема:**
В Неделе 4 в `process_video_task` нет шага генерации скриншотов для топ-10 ошибок!

**Текущий код (НЕПОЛНЫЙ):**
```python
# 6. Сохранить в БД
for err_data in top_10_errors:
    error = Error(
        analysis_id=analysis.id,
        timestamp=err_data['timestamp'],
        # ... другие поля
    )
    db.add(error)
```

**ИСПРАВЛЕНИЕ:**
```python
# 6. Генерация скриншотов ДО сохранения в БД
from app.services.visualization_service import visualization_service

for err_data in top_10_errors:
    # Сгенерировать скриншот с разметкой
    screenshot_path = visualization_service.create_error_screenshot(
        video_path=video_path,
        timestamp=err_data['timestamp'],
        error_data=err_data,
        detected_element=err_data.get('detected_element')
    )
    err_data['screenshot_path'] = screenshot_path

# 7. Теперь сохранить в БД со скриншотами
for err_data in top_10_errors:
    error = Error(
        analysis_id=analysis.id,
        timestamp=err_data['timestamp'],
        category=err_data['category'],
        severity=err_data['severity'],
        description=err_data['description'],
        recommendation=err_data['recommendation'],
        screenshot_path=err_data.get('screenshot_path'),  # ← ДОБАВЛЕНО
        detected_element=err_data.get('detected_element')
    )
    db.add(error)
```

**Где добавить:** Неделя 4, День 9-10, в `process_video_task`

---

### 2. **Отсутствует API endpoint для сохранения результата**

**Проблема:**
План описывает кнопки "Сохранить/Не сохранять" на ResultsPage, но нет API endpoint!

**ИСПРАВЛЕНИЕ:**
Добавить в `backend/app/api/videos.py`:

```python
@router.post("/analyses/{analysis_id}/save")
def save_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Сохранить результат анализа:
    1. Переместить видео из temp/ в saved/
    2. Установить Video.is_saved = True
    3. Удалить запись из TempUploads
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    if analysis.video.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    video = analysis.video
    
    # Переместить файл
    old_path = video.file_path
    new_path = old_path.replace('/temp/', '/saved/')
    
    os.makedirs(os.path.dirname(new_path), exist_ok=True)
    shutil.move(old_path, new_path)
    
    video.file_path = new_path
    video.is_saved = True
    
    # Удалить из TempUploads
    temp_upload = db.query(TempUpload).filter(
        TempUpload.user_id == current_user.id,
        TempUpload.file_path == old_path
    ).first()
    if temp_upload:
        db.delete(temp_upload)
    
    db.commit()
    
    return {"status": "saved", "video_id": video.id}


@router.delete("/analyses/{analysis_id}")
def discard_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Отклонить результат:
    1. Удалить видео файл
    2. Удалить все скриншоты
    3. Удалить записи из БД (каскадное удаление)
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    if analysis.video.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    video = analysis.video
    
    # Удалить видео файл
    if os.path.exists(video.file_path):
        os.remove(video.file_path)
    
    # Удалить скриншоты
    for error in analysis.errors:
        if error.screenshot_path and os.path.exists(error.screenshot_path):
            os.remove(error.screenshot_path)
    
    # Удалить из БД (каскадное удаление Analysis → Errors)
    db.delete(video)
    db.commit()
    
    return {"status": "deleted"}
```

**Где добавить:** Неделя 4, День 9-10, в `backend/app/api/videos.py`

---

### 3. **Неправильная схема БД для скриншотов**

**Проблема:**
В модели `Error` есть два поля:
- `screenshot_path` 
- `reference_screenshot_path`

Но мы решили делать ОДИН композитный скриншот (красный + зелёный на одном изображении).

**ИСПРАВЛЕНИЕ:**
Убрать `reference_screenshot_path` из модели:

```python
class Error(Base):
    __tablename__ = "errors"
    
    # ... другие поля
    
    screenshot_path = Column(Text)  # ← ОДИН путь к композитному скриншоту
    # reference_screenshot_path - УДАЛИТЬ это поле
```

**Где исправить:** Неделя 1, День 2, в `backend/app/models/error.py`

---

## ⚠️ ВАЖНЫЕ ПРОБЛЕМЫ

### 4. **Отсутствует логика очистки временных файлов**

**Проблема:**
TempUploads имеет поле `expires_at`, но нет Celery задачи для очистки истёкших файлов.

**ИСПРАВЛЕНИЕ:**
Добавить периодическую Celery задачу:

```python
# backend/app/tasks/cleanup_tasks.py

from celery import Task
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.temp_upload import TempUpload
from datetime import datetime
import os

@celery_app.task
def cleanup_expired_uploads():
    """
    Периодическая задача (каждые 1 час):
    Удаляет истёкшие временные файлы
    """
    db = SessionLocal()
    
    try:
        # Найти истёкшие
        expired = db.query(TempUpload).filter(
            TempUpload.expires_at < datetime.utcnow()
        ).all()
        
        for temp in expired:
            # Удалить файл
            if os.path.exists(temp.file_path):
                os.remove(temp.file_path)
            
            # Удалить запись
            db.delete(temp)
        
        db.commit()
        
        return {"deleted": len(expired)}
        
    finally:
        db.close()


# Настроить периодический запуск (в celery_app.py)
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'cleanup-expired-uploads': {
        'task': 'app.tasks.cleanup_tasks.cleanup_expired_uploads',
        'schedule': crontab(minute=0),  # Каждый час
    },
}
```

**Где добавить:** Неделя 4, День 10, создать новый файл `backend/app/tasks/cleanup_tasks.py`

---

### 5. **Двойная обработка видео (неоптимально, но не критично)**

**Проблема:**
В `process_video_task`:
1. `rhythm_service.analyze_rhythm()` открывает видео и обрабатывает ВСЕ кадры через MediaPipe
2. `frame_extractor.extract_key_frames()` СНОВА открывает видео и извлекает 100 кадров

Это дублирование работы.

**ТЕКУЩИЙ КОД:**
```python
# 1. Локальный анализ ритма
rhythm_result = rhythm_service.analyze_rhythm(video_path)
# ↑ Внутри: pose_service.extract_poses_from_video() обрабатывает все 3600 кадров

# 2. Извлечь кадры для Claude
frames = frame_extractor.extract_key_frames(video_path, 100)
# ↑ Снова открывает видео и извлекает 100 кадров
```

**РЕШЕНИЕ (ОПЦИОНАЛЬНО для оптимизации):**
Можно было бы извлечь все кадры один раз и использовать повторно, но это усложнит код.

**ДЛЯ MVP: оставить как есть**
- Время обработки всё равно приемлемое (3-5 мин)
- Код проще и понятнее
- Можно оптимизировать позже

**Статус:** Не критично, оставить как есть для MVP.

---

### 6. **Уточнение: зачем MediaPipe на всех кадрах?**

**Вопрос:** Зачем обрабатывать MediaPipe на всех 3600 кадрах, если Claude получает только 100?

**ОТВЕТ:**
MediaPipe на всех кадрах нужен ТОЛЬКО для анализа ритма:
1. Извлекаем позы из всех кадров (3600 кадров)
2. Определяем шаги по движению стоп
3. Сопоставляем шаги с битами музыки

Для Claude (постура/техника) MediaPipe НЕ НУЖЕН - Claude получает просто 100 JPEG изображений.

**Уточнение в плане:**
```python
# ШАГ 1: MediaPipe на всех кадрах (ТОЛЬКО для ритма)
poses = pose_service.extract_poses_from_video(video_path)
steps = pose_service.detect_steps(poses)
rhythm_errors = compare_steps_with_beats(steps, beats)

# ШАГ 2: Извлечь 100 кадров как изображения (для Claude)
# MediaPipe здесь НЕ запускается!
frames_jpeg = frame_extractor.extract_key_frames(video_path, 100)

# ШАГ 3: Отправить изображения в Claude
claude_result = claude_service.analyze_video(frames_jpeg, rhythm_errors)
```

**Где уточнить:** В комментариях к коду Недели 4.

---

## 📝 СРЕДНИЕ ПРОБЛЕМЫ

### 7. **Frontend недели (5-7) описаны слишком кратко**

**Проблема:**
В плане Неделя 5-6 описана одной строкой "Upload Page - drag & drop".

**ИСПРАВЛЕНИЕ:**
Детализировать:

**Неделя 5: Upload Page**
- День 11-12: VideoUploader компонент (drag & drop, валидация)
- День 13: Интеграция с API, прогресс-бар загрузки
- День 14-15: ProcessingPage (polling статуса, прогресс обработки)

**Неделя 6: Processing UI детально**
- День 16: Прогресс-бар с этапами
- День 17: Кнопка отмены
- День 18: Error handling

**Неделя 7: Results Page детально**
- День 19-20: VideoPlayer + ErrorsList компонент
- День 21: ErrorCard компонент с скриншотами
- День 22: ScoresSummary компонент
- День 23: Кнопки "Сохранить"/"Не сохранять"

**Где добавить:** Расширить описание Недель 5-7 в плане.

---

### 8. **Тестирование (Неделя 9-10) не детализировано**

**Проблема:**
"Баг-фиксинг, тестирование" - что именно?

**ИСПРАВЛЕНИЕ:**

**Неделя 9: Unit тесты**
- День 24-25: Backend тесты (сервисы, API endpoints)
- День 26-27: Frontend тесты (компоненты, hooks)

**Неделя 10: Integration и E2E тесты**
- День 28-29: E2E тесты (полный цикл: загрузка → обработка → результат)
- День 30: Performance тесты, баг-фиксинг

**Где добавить:** Детализировать Недели 9-10 в плане.

---

## ✅ ИСПРАВЛЕННЫЙ ПОРЯДОК ОПЕРАЦИЙ В CELERY ЗАДАЧЕ

**ПРАВИЛЬНАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ:**

```python
@celery_app.task(bind=True)
def process_video_task(self: Task, video_id: int, video_path: str):
    db = SessionLocal()
    
    try:
        analysis = db.query(Analysis).filter(Analysis.video_id == video_id).first()
        analysis.status = "processing"
        db.commit()
        
        start_time = time.time()
        
        # ШАГ 1: Локальный анализ ритма
        # (MediaPipe на всех кадрах для определения шагов)
        rhythm_result = rhythm_service.analyze_rhythm(video_path)
        
        # ШАГ 2: Извлечь 100 ключевых кадров для Claude
        # (Просто JPEG изображения, без MediaPipe)
        frames = frame_extractor.extract_key_frames(video_path, 100)
        
        # ШАГ 3: Отправить в Claude API
        # (Claude анализирует постуру/технику/музыкальность)
        claude_result = claude_service.analyze_video(frames, rhythm_result['errors'])
        
        # ШАГ 4: Объединить ошибки
        all_errors = rhythm_result['errors'] + claude_result.get('errors', [])
        
        # ШАГ 5: Отобрать топ-10 по severity
        all_errors.sort(key=lambda e: severity_priority(e['severity']))
        top_10_errors = all_errors[:10]
        
        # ШАГ 6: Генерация скриншотов для топ-10 ошибок ← ДОБАВЛЕНО!
        for err_data in top_10_errors:
            screenshot_path = visualization_service.create_error_screenshot(
                video_path=video_path,
                timestamp=err_data['timestamp'],
                error_data=err_data,
                detected_element=err_data.get('detected_element')
            )
            err_data['screenshot_path'] = screenshot_path
        
        # ШАГ 7: Сохранить в БД
        analysis.status = "completed"
        analysis.rhythm_score = rhythm_result['rhythm_score']
        analysis.posture_score = claude_result.get('posture_score', 0)
        analysis.technique_score = claude_result.get('technique_score', 0)
        analysis.musicality_score = claude_result.get('musicality_score', 0)
        analysis.overall_score = (
            analysis.rhythm_score + analysis.posture_score +
            analysis.technique_score + analysis.musicality_score
        ) / 4
        analysis.total_errors = len(top_10_errors)
        analysis.processing_time = int(time.time() - start_time)
        
        for err_data in top_10_errors:
            error = Error(
                analysis_id=analysis.id,
                timestamp=err_data['timestamp'],
                category=err_data['category'],
                severity=err_data['severity'],
                title=err_data.get('title', ''),
                description=err_data['description'],
                recommendation=err_data['recommendation'],
                screenshot_path=err_data.get('screenshot_path'),  # ← ДОБАВЛЕНО!
                detected_element=err_data.get('detected_element')
            )
            db.add(error)
        
        db.commit()
        
        return {"status": "success", "analysis_id": analysis.id}
        
    except Exception as e:
        analysis.status = "failed"
        analysis.error_message = str(e)
        db.commit()
        raise
    
    finally:
        db.close()
```

---

## 📊 ИТОГОВЫЙ ЧЕК-ЛИСТ ИСПРАВЛЕНИЙ

### Критические (блокируют работу):
- [ ] Добавить генерацию скриншотов в `process_video_task`
- [ ] Добавить API endpoints: `POST /analyses/{id}/save`, `DELETE /analyses/{id}`
- [ ] Убрать `reference_screenshot_path` из модели Error

### Важные (влияют на качество):
- [ ] Добавить Celery задачу очистки временных файлов
- [ ] Уточнить комментарии: MediaPipe для ритма, 100 кадров для Claude

### Средние (улучшают план):
- [ ] Детализировать Frontend недели (5-7)
- [ ] Детализировать тестирование (Недели 9-10)
- [ ] Добавить описание VisualizationService (Неделя 3)

---

## ✅ ВЕРДИКТ

**План в целом логичен и работоспособен.**

Найдено **3 критических** проблемы, которые ОБЯЗАТЕЛЬНО нужно исправить:
1. Генерация скриншотов
2. API для сохранения
3. Схема БД

Остальные проблемы - улучшения и уточнения, не блокирующие разработку.

**Рекомендация:** Внести критические исправления перед началом разработки.
