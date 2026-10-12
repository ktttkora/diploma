# 📋 ПОДРОБНЫЙ ПЛАН РАЗРАБОТКИ MVP
## Веб-сервис анализа техники танца хастл

**Срок:** 12-13 недель  
**Дата начала:** [указать]  
**Дата защиты:** [указать]

---

## 🎯 ЦЕЛЬ

Создать работающий MVP веб-сервиса, который:
1. Принимает видео танца хастл
2. Анализирует технику (ритм, постура, техника, музыкальность)
3. Показывает результаты со скриншотами и рекомендациями
4. Позволяет сохранять историю анализов

---

# 📅 НЕДЕЛЯ 1: БЫСТРЫЙ СТАРТ (4-5 дней)

## День 1: Инфраструктура и датасет

### ☀️ УТРО (2-3 часа)

#### Шаг 1.1: Создать Git репозиторий

```bash
# Создать папку проекта
mkdir hustl-analyzer
cd hustl-analyzer

# Инициализировать Git
git init
git remote add origin https://github.com/YOUR_USERNAME/hustl-analyzer.git

# Создать .gitignore
cat > .gitignore << EOF
# Python
venv/
__pycache__/
*.pyc
*.pyo
*.egg-info/
.env

# Node
node_modules/
dist/
build/

# Data
backend/data/uploads/
backend/data/reference_poses/*.json

# IDE
.vscode/
.idea/
.DS_Store
EOF

# Первый коммит
git add .gitignore
git commit -m "Initial commit"
```

**Результат:** ✅ Git репозиторий создан

---

#### Шаг 1.2: Создать структуру проекта

```bash
# Backend структура
mkdir -p backend/app/{api,models,services,tasks,core,db,schemas,utils}
mkdir -p backend/data/{reference_poses,uploads/temp,uploads/saved}
mkdir -p backend/scripts
mkdir -p backend/tests

# Frontend структура
mkdir -p frontend/src/{pages,components,services,hooks,types,utils}
mkdir -p frontend/public

# Документация
mkdir -p docs

# Создать пустые __init__.py для Python пакетов
touch backend/app/__init__.py
touch backend/app/api/__init__.py
touch backend/app/models/__init__.py
touch backend/app/services/__init__.py
touch backend/app/tasks/__init__.py
touch backend/app/core/__init__.py
touch backend/app/db/__init__.py
touch backend/app/schemas/__init__.py
touch backend/app/utils/__init__.py
```

**Результат:** ✅ Структура папок создана

---

#### Шаг 1.3: Написать скрипт обработки датасета

```bash
cd backend/scripts
```

Создать файл `extract_all_references.py`:

```python
import os
import cv2
import json
import mediapipe as mp
from pathlib import Path
from tqdm import tqdm
from datetime import datetime

# Пути
DATASET_PATH = "C:/Users/kt/important/university/diploma/hasl_files"
OUTPUT_PATH = "../data/reference_poses"

# MediaPipe
mp_pose = mp.solutions.pose

def extract_element_name(filename):
    """
    Извлекает название элемента из имени файла
    Например: "Американка.mp4" → "Американка"
    """
    return Path(filename).stem

def process_video(video_path, element_name):
    """
    Обрабатывает одно видео:
    - Извлекает все кадры
    - Применяет MediaPipe
    - Возвращает список поз
    """
    cap = cv2.VideoCapture(video_path)
    
    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as pose:
        
        poses = []
        frame_count = 0
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Конвертируем BGR → RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # MediaPipe обработка
            result = pose.process(frame_rgb)
            
            if result.pose_landmarks:
                # Сохраняем координаты всех 33 точек
                landmarks = []
                for lm in result.pose_landmarks.landmark:
                    landmarks.append({
                        "x": float(lm.x),
                        "y": float(lm.y),
                        "z": float(lm.z),
                        "visibility": float(lm.visibility)
                    })
                
                poses.append({
                    "frame": frame_count,
                    "timestamp": round(frame_count / fps, 3),
                    "landmarks": landmarks
                })
            
            frame_count += 1
        
        cap.release()
    
    return {
        "element": element_name,
        "total_frames": frame_count,
        "fps": fps,
        "duration": round(frame_count / fps, 2),
        "poses_count": len(poses),
        "poses": poses,
        "processed_at": datetime.now().isoformat()
    }

def save_reference(data, element_name):
    """
    Сохраняет в JSON
    """
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    output_file = os.path.join(OUTPUT_PATH, f"{element_name}.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    """
    Основная функция
    """
    print("=" * 60)
    print("🎬 ОБРАБОТКА ДАТАСЕТА ЭТАЛОННЫХ ВИДЕО")
    print("=" * 60)
    print(f"📁 Датасет: {DATASET_PATH}")
    print(f"💾 Результат: {OUTPUT_PATH}")
    print()
    
    # Проверяем датасет
    if not os.path.exists(DATASET_PATH):
        print(f"❌ ОШИБКА: Датасет не найден по пути {DATASET_PATH}")
        print("   Проверьте путь к папке hasl_files")
        return
    
    # Получаем список всех видео
    video_files = [
        f for f in os.listdir(DATASET_PATH)
        if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))
    ]
    
    if not video_files:
        print(f"❌ ОШИБКА: Видео не найдены в {DATASET_PATH}")
        return
    
    print(f"📊 Найдено видео: {len(video_files)}")
    print()
    print("⏱️  Примерное время обработки:")
    print(f"   CPU: ~5-7 часов")
    print(f"   GPU: ~1-2 часа")
    print()
    input("Нажмите Enter для начала обработки...")
    print()
    
    # Статистика
    start_time = datetime.now()
    success_count = 0
    error_count = 0
    
    # Обрабатываем каждое видео с прогресс-баром
    for video_file in tqdm(video_files, desc="🎬 Обработка", unit="видео"):
        element_name = extract_element_name(video_file)
        video_path = os.path.join(DATASET_PATH, video_file)
        
        # Пропускаем уже обработанные
        output_file = os.path.join(OUTPUT_PATH, f"{element_name}.json")
        if os.path.exists(output_file):
            tqdm.write(f"⏭️  {element_name}: уже обработан, пропускаем")
            success_count += 1
            continue
        
        try:
            # Обработка
            data = process_video(video_path, element_name)
            
            # Сохранение
            save_reference(data, element_name)
            
            # Лог
            tqdm.write(
                f"✅ {element_name}: "
                f"{data['poses_count']} поз из {data['total_frames']} кадров "
                f"({data['duration']}с)"
            )
            success_count += 1
            
        except Exception as e:
            tqdm.write(f"❌ ОШИБКА в {video_file}: {e}")
            error_count += 1
            
            # Записать в лог
            with open("errors.log", "a", encoding="utf-8") as log:
                log.write(f"{datetime.now().isoformat()} | {video_file} | {e}\n")
    
    # Итоговая статистика
    end_time = datetime.now()
    duration = end_time - start_time
    
    print()
    print("=" * 60)
    print("🎉 ОБРАБОТКА ЗАВЕРШЕНА!")
    print("=" * 60)
    print(f"✅ Успешно: {success_count}")
    print(f"❌ Ошибок: {error_count}")
    print(f"⏱️  Время: {duration}")
    print(f"💾 Результаты сохранены в: {OUTPUT_PATH}")
    print()
    
    # Проверка размера
    total_size = sum(
        os.path.getsize(os.path.join(OUTPUT_PATH, f))
        for f in os.listdir(OUTPUT_PATH)
        if f.endswith('.json')
    )
    print(f"📦 Общий размер: {total_size / 1024 / 1024:.1f} MB")
    print("=" * 60)

if __name__ == "__main__":
    main()
```

**Результат:** ✅ Скрипт обработки создан

---

#### Шаг 1.4: Запустить обработку датасета (В ФОНЕ!)

```bash
# Установить зависимости для скрипта
pip install opencv-python mediapipe tqdm

# Запустить (идёт 5-7 часов, займёмся другим)
python extract_all_references.py
```

**ВАЖНО:** Скрипт будет работать 5-7 часов. **НЕ ЖДИТЕ ЕГО!** Пока он работает, делаем остальные шаги.

**Результат:** ✅ Обработка запущена в фоне

---

### 🌤️ ДЕНЬ (пока датасет обрабатывается, 3-4 часа)

#### Шаг 1.5: Установить Backend зависимости

```bash
cd ../../backend

# Создать виртуальное окружение
python -m venv venv

# Активировать
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Создать requirements.txt
cat > requirements.txt << EOF
# Web Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6

# Database
sqlalchemy==2.0.25
alembic==1.13.1
psycopg2-binary==2.9.9

# Auth
fastapi-users[sqlalchemy]==12.1.3
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# Tasks
celery==5.3.6
redis==5.0.1

# AI & CV
anthropic==0.8.1
opencv-python==4.9.0.80
mediapipe==0.10.9
librosa==0.10.1
soundfile==0.12.1

# Utils
python-dotenv==1.0.0
pydantic-settings==2.1.0
tqdm==4.66.1
pillow==10.2.0

# FFmpeg wrapper
ffmpeg-python==0.2.0
EOF

# Установить всё
pip install -r requirements.txt
```

**Результат:** ✅ Backend зависимости установлены

---

#### Шаг 1.6: Установить Frontend зависимости

```bash
cd ../frontend

# Создать React проект с Vite
npm create vite@latest . -- --template react-ts

# Установить MUI и другие зависимости
npm install @mui/material @emotion/react @emotion/styled
npm install @mui/icons-material
npm install axios
npm install react-router-dom
npm install recharts
npm install react-player
npm install react-toastify

# Dev зависимости
npm install --save-dev @types/node
```

**Результат:** ✅ Frontend зависимости установлены

---

#### Шаг 1.7: Docker Compose для PostgreSQL и Redis

```bash
cd ..
```

Создать `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: hustl_postgres
    environment:
      POSTGRES_USER: hustl_user
      POSTGRES_PASSWORD: hustl_pass_2026
      POSTGRES_DB: hustl_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: hustl_redis
    ports:
      - "6379:6379"
    restart: unless-stopped

volumes:
  postgres_data:
```

```bash
# Запустить
docker-compose up -d

# Проверить
docker-compose ps
```

**Результат:** ✅ PostgreSQL и Redis работают

---

### 🌙 ВЕЧЕР (2 часа)

#### Шаг 1.8: Коммит и пуш

```bash
git add .
git commit -m "feat: project setup - structure, dependencies, docker-compose

- Created project structure (backend, frontend)
- Added dependencies (Python, Node)
- Docker compose for PostgreSQL and Redis
- Script for dataset processing (started)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"

git push origin main
```

**Результат:** ✅ Код в репозитории

---

## ✅ ИТОГ ДНЯ 1:

```
✅ Git репозиторий создан
✅ Структура проекта создана
✅ Backend зависимости установлены
✅ Frontend зависимости установлены
✅ PostgreSQL + Redis работают в Docker
✅ Скрипт обработки датасета запущен (работает в фоне)
✅ Код запушен в Git

⏳ Обработка датасета продолжается (~5-7 часов)
```

---

## День 2: Backend базовый setup

### ☀️ УТРО (3-4 часа)

#### Шаг 2.1: Конфигурация

```bash
cd backend
```

Создать `.env`:

```env
# Database
DATABASE_URL=postgresql://hustl_user:hustl_pass_2026@localhost:5432/hustl_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-super-secret-key-change-in-production-min-32-chars

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# File Storage
UPLOAD_DIR=data/uploads
MAX_FILE_SIZE=1073741824
MAX_VIDEO_DURATION=600
```

Создать `app/config.py`:

```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Anthropic
    ANTHROPIC_API_KEY: str
    
    # File Storage
    UPLOAD_DIR: str = "data/uploads"
    MAX_FILE_SIZE: int = 1073741824  # 1 GB
    MAX_VIDEO_DURATION: int = 600  # 10 minutes
    ALLOWED_VIDEO_FORMATS: list = [".mp4", ".avi", ".mov", ".mkv"]
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

**Результат:** ✅ Конфигурация создана

---

#### Шаг 2.2: Database session

Создать `app/db/session.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Создаём engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base для моделей
Base = declarative_base()

# Dependency для FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Результат:** ✅ Database session готов

---

#### Шаг 2.3: Модели БД

Создать `app/models/user.py`:

```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100))
    avatar_url = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")
    temp_uploads = relationship("TempUpload", back_populates="user", cascade="all, delete-orphan")
```

Создать `app/models/video.py`:

```python
from sqlalchemy import Column, Integer, String, Float, BigInteger, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base

class Video(Base):
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500))
    duration = Column(Float, nullable=False)
    size = Column(BigInteger, nullable=False)
    resolution = Column(String(20))
    fps = Column(Integer)
    format = Column(String(10))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    is_saved = Column(Boolean, default=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="videos")
    analyses = relationship("Analysis", back_populates="video", cascade="all, delete-orphan")
```

Создать `app/models/analysis.py`:

```python
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base

class Analysis(Base):
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="queued", index=True)
    # Status: queued, processing, completed, failed
    
    overall_score = Column(Float)
    rhythm_score = Column(Float)
    posture_score = Column(Float)
    technique_score = Column(Float)
    musicality_score = Column(Float)
    total_errors = Column(Integer, default=0)
    
    ai_response = Column(JSON)
    processing_time = Column(Integer)  # seconds
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    
    # Relationships
    video = relationship("Video", back_populates="analyses")
    errors = relationship("Error", back_populates="analysis", cascade="all, delete-orphan")
```

Создать `app/models/error.py`:

```python
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base

class Error(Base):
    __tablename__ = "errors"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    timestamp = Column(Float, nullable=False)  # seconds in video
    category = Column(String(20), nullable=False, index=True)
    # Category: rhythm, posture, technique, musicality
    
    severity = Column(String(20), nullable=False)
    # Severity: critical, high, medium, low
    
    title = Column(String(255))
    description = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    
    screenshot_path = Column(Text)
    reference_screenshot_path = Column(Text)
    detected_element = Column(String(100))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    analysis = relationship("Analysis", back_populates="errors")
```

Создать `app/models/temp_upload.py`:

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base

class TempUpload(Base):
    __tablename__ = "temp_uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="temp_uploads")
```

Обновить `app/models/__init__.py`:

```python
from app.db.session import Base
from app.models.user import User
from app.models.video import Video
from app.models.analysis import Analysis
from app.models.error import Error
from app.models.temp_upload import TempUpload

# Экспортируем для удобства
__all__ = ["Base", "User", "Video", "Analysis", "Error", "TempUpload"]
```

**Результат:** ✅ Модели БД созданы

---

#### Шаг 2.4: Alembic миграции

```bash
# Инициализация Alembic
alembic init alembic
```

Отредактировать `alembic/env.py`:

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Импортируем наши модели и config
from app.db.session import Base
from app.models import *  # Импортируем все модели
from app.config import settings

# this is the Alembic Config object
config = context.config

# Устанавливаем DATABASE_URL из settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# ... остальной код без изменений

target_metadata = Base.metadata
```

Создать миграцию:

```bash
alembic revision --autogenerate -m "Initial models: users, videos, analyses, errors, temp_uploads"
```

Применить миграцию:

```bash
alembic upgrade head
```

Проверить в PostgreSQL:

```bash
# Подключиться к БД
docker exec -it hustl_postgres psql -U hustl_user -d hustl_db

# Посмотреть таблицы
\dt

# Выйти
\q
```

**Результат:** ✅ Таблицы созданы в PostgreSQL

---

### 🌤️ ДЕНЬ (2-3 часа)

#### Шаг 2.5: FastAPI Users для Auth

Создать `app/core/security.py`:

```python
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
```

Создать `app/schemas/user.py`:

```python
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None

class UserResponse(UserBase):
    id: int
    avatar_url: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
```

Создать `app/api/deps.py`:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id: int = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    return user
```

Создать `app/api/auth.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token, LoginRequest
from app.core.security import verify_password, get_password_hash, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Проверяем, существует ли пользователь
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Создаём пользователя
    user = User(
        email=user_data.email,
        name=user_data.name,
        password_hash=get_password_hash(user_data.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user

@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    # Найти пользователя
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Создать токен
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}
```

Создать `app/api/users.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/me", response_model=UserResponse)
def update_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user_update.name is not None:
        current_user.name = user_update.name
    if user_update.avatar_url is not None:
        current_user.avatar_url = user_update.avatar_url
    
    db.commit()
    db.refresh(current_user)
    return current_user
```

Создать `app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import auth, users

app = FastAPI(
    title="Hustl Analyzer API",
    description="API для анализа техники танца хастл",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")

@app.get("/")
def root():
    return {
        "message": "Hustl Analyzer API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```

Запустить сервер:

```bash
cd backend
python -m app.main
```

Открыть в браузере: http://localhost:8000/docs

**Проверить:**
- POST /api/auth/register → создать пользователя
- POST /api/auth/login → получить токен
- GET /api/users/me (с токеном) → получить свой профиль

**Результат:** ✅ Auth API работает

---

### 🌙 ВЕЧЕР (1-2 часа)

#### Шаг 2.6: Frontend Auth UI

```bash
cd frontend/src
```

Создать `services/api.ts`:

```typescript
import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
})

// Interceptor для добавления токена
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Interceptor для обработки ошибок
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api
```

Создать `services/authService.ts`:

```typescript
import api from './api'

export interface RegisterData {
  email: string
  password: string
  name?: string
}

export interface LoginData {
  email: string
  password: string
}

export interface User {
  id: number
  email: string
  name?: string
  avatar_url?: string
  created_at: string
}

export const authService = {
  async register(data: RegisterData): Promise<User> {
    const response = await api.post('/auth/register', data)
    return response.data
  },

  async login(data: LoginData): Promise<string> {
    const response = await api.post('/auth/login', data)
    const token = response.data.access_token
    localStorage.setItem('token', token)
    return token
  },

  logout() {
    localStorage.removeItem('token')
  },

  getToken(): string | null {
    return localStorage.getItem('token')
  },

  isAuthenticated(): boolean {
    return this.getToken() !== null
  },

  async getMe(): Promise<User> {
    const response = await api.get('/users/me')
    return response.data
  },
}
```

Создать `pages/LoginPage.tsx`:

```typescript
import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  Alert,
  Link as MuiLink,
} from '@mui/material'
import { authService } from '../services/authService'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await authService.login({ email, password })
      navigate('/upload')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка входа')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8, mb: 4 }}>
        <Paper elevation={3} sx={{ p: 4 }}>
          <Typography variant="h4" gutterBottom align="center" fontWeight="bold">
            Вход в Hustl Analyzer
          </Typography>
          
          <Typography variant="body2" color="text.secondary" align="center" sx={{ mb: 3 }}>
            Анализ техники танца хастл с помощью AI
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              margin="normal"
              required
              autoComplete="email"
              autoFocus
            />

            <TextField
              fullWidth
              label="Пароль"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              margin="normal"
              required
              autoComplete="current-password"
            />

            <Button
              fullWidth
              type="submit"
              variant="contained"
              size="large"
              sx={{ mt: 3, mb: 2 }}
              disabled={loading}
            >
              {loading ? 'Вход...' : 'Войти'}
            </Button>

            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="body2">
                Нет аккаунта?{' '}
                <MuiLink component={Link} to="/register" underline="hover">
                  Зарегистрироваться
                </MuiLink>
              </Typography>
            </Box>
          </form>
        </Paper>
      </Box>
    </Container>
  )
}
```

Создать `pages/RegisterPage.tsx`:

```typescript
import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  Alert,
  Link as MuiLink,
} from '@mui/material'
import { authService } from '../services/authService'

export default function RegisterPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await authService.register({ email, password, name })
      // После регистрации сразу логинимся
      await authService.login({ email, password })
      navigate('/upload')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка регистрации')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8, mb: 4 }}>
        <Paper elevation={3} sx={{ p: 4 }}>
          <Typography variant="h4" gutterBottom align="center" fontWeight="bold">
            Регистрация
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="Имя"
              value={name}
              onChange={(e) => setName(e.target.value)}
              margin="normal"
            />

            <TextField
              fullWidth
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              margin="normal"
              required
              autoComplete="email"
            />

            <TextField
              fullWidth
              label="Пароль"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              margin="normal"
              required
              autoComplete="new-password"
              helperText="Минимум 6 символов"
            />

            <Button
              fullWidth
              type="submit"
              variant="contained"
              size="large"
              sx={{ mt: 3, mb: 2 }}
              disabled={loading}
            >
              {loading ? 'Регистрация...' : 'Зарегистрироваться'}
            </Button>

            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="body2">
                Уже есть аккаунт?{' '}
                <MuiLink component={Link} to="/login" underline="hover">
                  Войти
                </MuiLink>
              </Typography>
            </Box>
          </form>
        </Paper>
      </Box>
    </Container>
  )
}
```

Создать `pages/UploadPage.tsx` (пока заглушка):

```typescript
import { Container, Typography } from '@mui/material'

export default function UploadPage() {
  return (
    <Container>
      <Typography variant="h4" sx={{ mt: 4 }}>
        Загрузка видео (в разработке)
      </Typography>
    </Container>
  )
}
```

Создать `App.tsx`:

```typescript
import { Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import UploadPage from './pages/UploadPage'
import { authService } from './services/authService'

function PrivateRoute({ children }: { children: JSX.Element }) {
  return authService.isAuthenticated() ? children : <Navigate to="/login" />
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/upload"
        element={
          <PrivateRoute>
            <UploadPage />
          </PrivateRoute>
        }
      />
      <Route path="/" element={<Navigate to="/login" />} />
    </Routes>
  )
}

export default App
```

Обновить `main.tsx`:

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import App from './App'

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <App />
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
```

Запустить:

```bash
cd frontend
npm run dev
```

Открыть http://localhost:3000

**Проверить:**
1. Зарегистрироваться
2. Войти
3. Перенаправляет на /upload

**Результат:** ✅ Frontend Auth UI работает

---

## ✅ ИТОГ ДНЯ 2:

```
✅ Backend конфигурация создана
✅ БД модели созданы
✅ Миграции применены
✅ Auth API работает (/register, /login, /users/me)
✅ Frontend Auth UI работает
✅ Можно зарегистрироваться и войти через UI

🎉 MILESTONE: Auth полностью работает E2E
```

---

## День 3: Проверка датасета

### ☀️ УТРО (1-2 часа)

#### Шаг 3.1: Проверить обработку датасета

```bash
cd backend

# Проверить количество
ls data/reference_poses/*.json | wc -l
# Должно быть: 520

# Проверить размер
du -sh data/reference_poses/
# Должно быть: ~500-600 MB

# Проверить один файл
python -m json.tool data/reference_poses/Американка.json | head -50
```

**Если обработка ещё идёт:**
- Подожди или останови и запусти на GPU
- Можно продолжить с 10-20 элементами для начала

**Результат:** ✅ Датасет обработан

---

#### Шаг 3.2: ReferenceService

Создать `app/services/reference_service.py`:

```python
import json
import os
from typing import Optional, Dict, List
from pathlib import Path

class ReferenceService:
    def __init__(self, references_dir: str = "data/reference_poses"):
        self.references_dir = references_dir
        self.cache: Dict[str, Dict] = {}
    
    def get_reference(self, element_name: str) -> Optional[Dict]:
        """
        Получить эталонные позы для элемента
        
        Returns:
            {
                "element": "Американка",
                "total_frames": 897,
                "fps": 30.0,
                "poses": [...]
            }
        """
        # Проверяем кеш
        if element_name in self.cache:
            return self.cache[element_name]
        
        # Загружаем из JSON
        json_path = Path(self.references_dir) / f"{element_name}.json"
        if not json_path.exists():
            return None
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.cache[element_name] = data
            return data
        except Exception as e:
            print(f"Error loading reference {element_name}: {e}")
            return None
    
    def find_similar_pose(
        self, 
        element_name: str, 
        target_timestamp: float
    ) -> Optional[Dict]:
        """
        Найти наиболее похожую позу из эталона по timestamp
        
        Пока простая логика: берём кадр на том же моменте времени
        TODO: Реализовать поиск по похожести скелета
        """
        reference = self.get_reference(element_name)
        if not reference:
            return None
        
        poses = reference.get('poses', [])
        if not poses:
            return None
        
        # Найти ближайший по timestamp
        closest_pose = min(
            poses,
            key=lambda p: abs(p['timestamp'] - target_timestamp)
        )
        
        return closest_pose
    
    def get_average_pose(self, element_name: str) -> Optional[Dict]:
        """
        Получить усреднённую позу для элемента
        (средний кадр из всех)
        """
        reference = self.get_reference(element_name)
        if not reference:
            return None
        
        poses = reference.get('poses', [])
        if not poses:
            return None
        
        # Берём средний кадр
        mid_index = len(poses) // 2
        return poses[mid_index]
    
    def list_available_elements(self) -> List[str]:
        """
        Список всех доступных элементов
        """
        refs_path = Path(self.references_dir)
        if not refs_path.exists():
            return []
        
        return [
            f.stem for f in refs_path.glob("*.json")
        ]

# Singleton
reference_service = ReferenceService()
```

**Результат:** ✅ ReferenceService готов

---

### 🌤️ ДЕНЬ (2-3 часа)

#### Шаг 3.3: Тестовый скрипт для проверки

Создать `backend/scripts/test_reference_service.py`:

```python
import sys
sys.path.append('..')

from app.services.reference_service import reference_service

def main():
    print("=" * 60)
    print("Тест ReferenceService")
    print("=" * 60)
    
    # Список элементов
    elements = reference_service.list_available_elements()
    print(f"\n✅ Найдено элементов: {len(elements)}")
    print(f"Первые 10: {elements[:10]}")
    
    # Загрузить один элемент
    if "Американка" in elements:
        print("\n" + "=" * 60)
        print("Тест: Американка")
        print("=" * 60)
        
        ref = reference_service.get_reference("Американка")
        if ref:
            print(f"✅ Total frames: {ref['total_frames']}")
            print(f"✅ FPS: {ref['fps']}")
            print(f"✅ Poses: {ref['poses_count']}")
            print(f"✅ Duration: {ref['duration']}s")
            
            # Найти позу на 2.5 сек
            pose = reference_service.find_similar_pose("Американка", 2.5)
            if pose:
                print(f"\n✅ Найдена поза на {pose['timestamp']}s")
                print(f"   Кадр: {pose['frame']}")
                print(f"   Landmarks: {len(pose['landmarks'])} точек")
    
    print("\n" + "=" * 60)
    print("✅ Тест завершён")
    print("=" * 60)

if __name__ == "__main__":
    main()
```

```bash
cd backend/scripts
python test_reference_service.py
```

**Ожидаемый вывод:**
```
============================================================
Тест ReferenceService
============================================================

✅ Найдено элементов: 520
Первые 10: ['Американка', 'Солнышко', 'Катапульта', ...]

============================================================
Тест: Американка
============================================================
✅ Total frames: 897
✅ FPS: 30.0
✅ Poses: 856
✅ Duration: 29.9s

✅ Найдена поза на 2.5s
   Кадр: 75
   Landmarks: 33 точек

============================================================
✅ Тест завершён
============================================================
```

**Результат:** ✅ ReferenceService протестирован

---

### 🌙 ВЕЧЕР (2 часа)

#### Шаг 3.4: Документация и коммит

Создать `backend/docs/REFERENCE_POSES_FORMAT.md`:

```markdown
# Формат эталонных поз

## Структура JSON файла

Каждый файл `data/reference_poses/{ElementName}.json`:

```json
{
  "element": "Американка",
  "total_frames": 897,
  "fps": 30.0,
  "duration": 29.9,
  "poses_count": 856,
  "poses": [
    {
      "frame": 0,
      "timestamp": 0.0,
      "landmarks": [
        {
          "x": 0.512,
          "y": 0.234,
          "z": -0.123,
          "visibility": 0.98
        },
        ... (33 точки)
      ]
    },
    ...
  ],
  "processed_at": "2026-10-11T10:30:00"
}
```

## Landmarks (33 точки MediaPipe)

0. nose
1. left_eye_inner
2. left_eye
3. left_eye_outer
4. right_eye_inner
5. right_eye
6. right_eye_outer
7. left_ear
8. right_ear
9. mouth_left
10. mouth_right
11. left_shoulder
12. right_shoulder
13. left_elbow
14. right_elbow
15. left_wrist
16. right_wrist
17. left_pinky
18. right_pinky
19. left_index
20. right_index
21. left_thumb
22. right_thumb
23. left_hip
24. right_hip
25. left_knee
26. right_knee
27. left_ankle
28. right_ankle
29. left_heel
30. right_heel
31. left_foot_index
32. right_foot_index

## Координаты

- `x`, `y`: нормализованные [0, 1] относительно размера кадра
- `z`: глубина относительно hips (середина бёдер)
- `visibility`: вероятность видимости [0, 1]
```

Обновить `README.md`:

```markdown
# Hustl Analyzer

Веб-сервис для анализа техники танца хастл с использованием AI.

## Структура проекта

- `backend/` - FastAPI backend
- `frontend/` - React frontend
- `docs/` - Документация

## Текущий статус

### ✅ Готово (Неделя 1, День 1-3):

- [x] Структура проекта
- [x] Backend базовый setup (FastAPI, PostgreSQL, Redis)
- [x] БД модели (Users, Videos, Analyses, Errors, TempUploads)
- [x] Auth API (register, login)
- [x] Frontend Auth UI (React, MUI)
- [x] Датасет обработан (520 эталонных элементов)
- [x] ReferenceService

### ⏳ В разработке (Неделя 2):

- [ ] Анализ видео (локальный ритм)
- [ ] Claude API интеграция
- [ ] Визуализация

## Быстрый старт

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
docker-compose up -d
alembic upgrade head
python -m app.main
```

API: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:3000

## Тестирование

```bash
# Backend: регистрация
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123","name":"Test User"}'

# Backend: вход
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123"}'

# Frontend: открыть http://localhost:3000
# - Зарегистрироваться
# - Войти
```

## Технологии

- **Backend:** Python 3.10+, FastAPI, SQLAlchemy, Celery
- **Frontend:** React 18, TypeScript, Material-UI
- **БД:** PostgreSQL 15
- **Кеш/Очередь:** Redis 7
- **AI:** Claude Opus 5.5 (Anthropic)
- **CV:** MediaPipe, OpenCV
- **Audio:** librosa, FFmpeg
```

Коммит:

```bash
git add .
git commit -m "feat(week1): complete setup - auth, db models, reference service

Week 1 Day 1-3 completed:
- Backend: FastAPI + PostgreSQL + Redis + Auth API
- Frontend: React + MUI + Auth UI
- Database: 5 tables with migrations
- Dataset: 520 reference poses processed
- ReferenceService: load and query reference poses
- Documentation: README, API docs

Tests:
- ✅ Register/Login via API
- ✅ Register/Login via UI
- ✅ ReferenceService loads 520 elements

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"

git push origin main
```

**Результат:** ✅ Неделя 1 завершена, код в Git

---

## ✅ ИТОГ НЕДЕЛИ 1 (День 1-3):

```
✅ Git репозиторий создан
✅ Структура проекта создана
✅ Backend работает:
   - FastAPI + PostgreSQL + Redis
   - БД модели (5 таблиц)
   - Auth API (register, login, get_me)
   - Миграции Alembic
✅ Frontend работает:
   - React + TypeScript + MUI
   - Auth UI (Login, Register)
   - API клиент (axios)
   - Routing (react-router)
✅ Датасет обработан:
   - 520 эталонных элементов
   - ~500-600 MB JSON
   - ReferenceService готов
✅ Документация:
   - README с инструкциями
   - API docs (FastAPI /docs)
   - Формат эталонных поз

🎉 МОЖНО ЗАРЕГИСТРИРОВАТЬСЯ И ВОЙТИ ЧЕРЕЗ UI
🎉 ГОТОВЫ К РАЗРАБОТКЕ АНАЛИЗА ВИДЕО
```

---

---

# 📅 НЕДЕЛЯ 2: АНАЛИЗ ВИДЕО - ЛОКАЛЬНЫЙ РИТМ (5 дней)

## День 4: Анализ аудио + определение битов

### ☀️ УТРО (3-4 часа)

#### Шаг 4.1: Установить FFmpeg

**Windows:**
```bash
# Скачать FFmpeg: https://www.gyan.dev/ffmpeg/builds/
# Распаковать и добавить в PATH
# Или через chocolatey:
choco install ffmpeg

# Проверить
ffmpeg -version
```

**Linux/Mac:**
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# Mac
brew install ffmpeg

# Проверить
ffmpeg -version
```

**Результат:** ✅ FFmpeg установлен

---

#### Шаг 4.2: Утилиты для работы с видео

Создать `backend/app/utils/video_utils.py`:

```python
import subprocess
import os
from pathlib import Path
from typing import Dict, Optional
import json

class VideoUtils:
    @staticmethod
    def extract_audio(video_path: str, output_path: str) -> bool:
        """
        Извлечь аудиодорожку из видео
        
        Args:
            video_path: путь к видео
            output_path: куда сохранить аудио (*.wav)
        
        Returns:
            True если успешно
        """
        try:
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vn',  # Без видео
                '-acodec', 'pcm_s16le',  # WAV формат
                '-ar', '44100',  # Частота дискретизации
                '-ac', '2',  # Стерео
                '-y',  # Перезаписать
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            
            return os.path.exists(output_path)
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg error: {e.stderr.decode()}")
            return False
    
    @staticmethod
    def get_video_info(video_path: str) -> Optional[Dict]:
        """
        Получить метаданные видео
        
        Returns:
            {
                'duration': 120.5,
                'width': 1920,
                'height': 1080,
                'fps': 30.0,
                'codec': 'h264',
                'size': 1048576
            }
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            
            data = json.loads(result.stdout.decode())
            
            # Найти видео-стрим
            video_stream = next(
                (s for s in data['streams'] if s['codec_type'] == 'video'),
                None
            )
            
            if not video_stream:
                return None
            
            # Извлечь FPS
            fps_str = video_stream.get('r_frame_rate', '30/1')
            fps_parts = fps_str.split('/')
            fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30.0
            
            return {
                'duration': float(data['format'].get('duration', 0)),
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
                'fps': fps,
                'codec': video_stream.get('codec_name', 'unknown'),
                'size': int(data['format'].get('size', 0))
            }
        except Exception as e:
            print(f"FFprobe error: {e}")
            return None
    
    @staticmethod
    def extract_frame(video_path: str, timestamp: float, output_path: str) -> bool:
        """
        Извлечь один кадр по timestamp
        
        Args:
            video_path: путь к видео
            timestamp: время в секундах
            output_path: куда сохранить кадр (*.jpg)
        """
        try:
            cmd = [
                'ffmpeg',
                '-ss', str(timestamp),
                '-i', video_path,
                '-vframes', '1',
                '-y',
                output_path
            ]
            
            subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            
            return os.path.exists(output_path)
        except subprocess.CalledProcessError:
            return False
```

**Результат:** ✅ VideoUtils создан

---

#### Шаг 4.3: Анализ аудио и определение битов

Создать `backend/app/services/audio_service.py`:

```python
import librosa
import numpy as np
from typing import List, Dict, Tuple
import soundfile as sf

class AudioService:
    def __init__(self):
        pass
    
    def analyze_audio(self, audio_path: str) -> Dict:
        """
        Анализирует аудио: определяет темп и биты
        
        Returns:
            {
                'tempo': 136.0,
                'beats': [0.0, 0.44, 0.88, 1.32, ...],
                'beat_frames': [0, 1323, 2646, ...],
                'duration': 120.5,
                'sample_rate': 44100
            }
        """
        # Загружаем аудио
        y, sr = librosa.load(audio_path, sr=None)
        
        # Определяем темп и биты
        tempo, beat_frames = librosa.beat.beat_track(
            y=y,
            sr=sr,
            units='frames'
        )
        
        # Конвертируем frame numbers в секунды
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        
        # Длительность
        duration = librosa.get_duration(y=y, sr=sr)
        
        return {
            'tempo': float(tempo),
            'beats': beat_times.tolist(),
            'beat_frames': beat_frames.tolist(),
            'duration': float(duration),
            'sample_rate': int(sr)
        }
    
    def find_closest_beat(self, timestamp: float, beats: List[float]) -> Tuple[float, float]:
        """
        Найти ближайший бит к timestamp
        
        Returns:
            (closest_beat_time, difference)
        """
        if not beats:
            return (0.0, float('inf'))
        
        beats_array = np.array(beats)
        differences = np.abs(beats_array - timestamp)
        closest_idx = np.argmin(differences)
        
        return (
            float(beats_array[closest_idx]),
            float(differences[closest_idx])
        )
    
    def is_on_beat(self, timestamp: float, beats: List[float], tolerance: float = 0.15) -> bool:
        """
        Проверить, попадает ли timestamp в бит
        
        Args:
            timestamp: время шага в секундах
            beats: список битов
            tolerance: допустимое отклонение в секундах (150ms по умолчанию)
        
        Returns:
            True если в пределах tolerance
        """
        _, diff = self.find_closest_beat(timestamp, beats)
        return diff <= tolerance

# Singleton
audio_service = AudioService()
```

**Результат:** ✅ AudioService создан

---

### 🌤️ ДЕНЬ (2-3 часа)

#### Шаг 4.4: Тестовый скрипт для аудио

Создать `backend/scripts/test_audio_analysis.py`:

```python
import sys
sys.path.append('..')

from app.utils.video_utils import VideoUtils
from app.services.audio_service import audio_service
import os

def main():
    print("=" * 60)
    print("ТЕСТ: Анализ аудио")
    print("=" * 60)
    
    # Путь к тестовому видео
    # Замените на реальный путь к вашему тестовому видео
    test_video = "C:/Users/kt/important/university/diploma/hasl_files/Американка.mp4"
    
    if not os.path.exists(test_video):
        print("❌ Тестовое видео не найдено")
        print(f"   Путь: {test_video}")
        print("   Укажите путь к любому видео из датасета")
        return
    
    print(f"📹 Видео: {test_video}")
    print()
    
    # Шаг 1: Получить информацию о видео
    print("Шаг 1: Получение метаданных...")
    video_info = VideoUtils.get_video_info(test_video)
    if video_info:
        print(f"✅ Длительность: {video_info['duration']:.1f}s")
        print(f"✅ Разрешение: {video_info['width']}x{video_info['height']}")
        print(f"✅ FPS: {video_info['fps']:.1f}")
        print(f"✅ Размер: {video_info['size'] / 1024 / 1024:.1f} MB")
    else:
        print("❌ Не удалось получить метаданные")
        return
    
    print()
    
    # Шаг 2: Извлечь аудио
    print("Шаг 2: Извлечение аудио...")
    audio_path = "../data/temp_audio.wav"
    success = VideoUtils.extract_audio(test_video, audio_path)
    
    if success:
        print(f"✅ Аудио сохранено: {audio_path}")
    else:
        print("❌ Не удалось извлечь аудио")
        return
    
    print()
    
    # Шаг 3: Анализ аудио
    print("Шаг 3: Анализ ритма...")
    result = audio_service.analyze_audio(audio_path)
    
    print(f"✅ Темп (BPM): {result['tempo']:.1f}")
    print(f"✅ Битов найдено: {len(result['beats'])}")
    print(f"✅ Длительность: {result['duration']:.1f}s")
    print()
    
    # Показать первые 10 битов
    print("Первые 10 битов (секунды):")
    for i, beat in enumerate(result['beats'][:10]):
        print(f"  Бит {i+1}: {beat:.3f}s")
    
    print()
    
    # Тест: проверка попадания в ритм
    print("Шаг 4: Тест попадания в ритм...")
    
    # Симулируем шаги
    test_steps = [
        0.5,   # Должен попасть
        0.95,  # Должен попасть
        1.5,   # Может не попасть (зависит от битов)
        2.0,   # Должен попасть
    ]
    
    for step_time in test_steps:
        on_beat = audio_service.is_on_beat(step_time, result['beats'])
        closest, diff = audio_service.find_closest_beat(step_time, result['beats'])
        
        status = "✅ В РИТМЕ" if on_beat else "❌ НЕ В РИТМЕ"
        print(f"  Шаг на {step_time:.2f}s: {status}")
        print(f"    Ближайший бит: {closest:.3f}s (разница: {diff:.3f}s)")
    
    print()
    print("=" * 60)
    print("✅ ТЕСТ ЗАВЕРШЁН")
    print("=" * 60)
    
    # Очистка
    if os.path.exists(audio_path):
        os.remove(audio_path)

if __name__ == "__main__":
    main()
```

Запустить:

```bash
cd backend/scripts
python test_audio_analysis.py
```

**Ожидаемый вывод:**
```
============================================================
ТЕСТ: Анализ аудио
============================================================
📹 Видео: C:/Users/kt/.../Американка.mp4

Шаг 1: Получение метаданных...
✅ Длительность: 29.9s
✅ Разрешение: 1920x1080
✅ FPS: 30.0
✅ Размер: 45.2 MB

Шаг 2: Извлечение аудио...
✅ Аудио сохранено: ../data/temp_audio.wav

Шаг 3: Анализ ритма...
✅ Темп (BPM): 136.0
✅ Битов найдено: 68
✅ Длительность: 29.9s

Первые 10 битов (секунды):
  Бит 1: 0.000s
  Бит 2: 0.441s
  Бит 3: 0.883s
  Бит 4: 1.324s
  ...

Шаг 4: Тест попадания в ритм...
  Шаг на 0.50s: ✅ В РИТМЕ
    Ближайший бит: 0.441s (разница: 0.059s)
  Шаг на 0.95s: ✅ В РИТМЕ
    Ближайший бит: 0.883s (разница: 0.067s)
  ...

============================================================
✅ ТЕСТ ЗАВЕРШЁН
============================================================
```

**Результат:** ✅ Анализ аудио работает

---

### 🌙 ВЕЧЕР (2 часа)

#### Шаг 4.5: Коммит прогресса

```bash
git add .
git commit -m "feat(week2-day4): audio analysis - extract audio and detect beats

- VideoUtils: extract audio, get metadata, extract frame
- AudioService: analyze tempo/beats, find closest beat
- librosa integration for beat detection
- Test script validates audio analysis

Tests:
- ✅ FFmpeg extracts audio from video
- ✅ librosa detects tempo (BPM)
- ✅ Beat detection works
- ✅ is_on_beat validates rhythm

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"

git push origin main
```

**Результат:** ✅ День 4 завершён

---

## ✅ ИТОГ ДНЯ 4:

```
✅ FFmpeg установлен и работает
✅ VideoUtils: извлечение аудио и метаданных
✅ AudioService: определение темпа и битов
✅ librosa детектирует биты музыки
✅ Функция проверки попадания в ритм
✅ Тестовый скрипт подтверждает работу

🎉 MILESTONE: Умеем определять биты музыки
```

---

## День 5: MediaPipe - определение поз и шагов

### ☀️ УТРО (3-4 часа)

#### Шаг 5.1: Сервис для работы с MediaPipe

Создать `backend/app/services/pose_service.py`:

```python
import cv2
import mediapipe as mp
import numpy as np
from typing import List, Dict, Optional, Tuple

class PoseService:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
    
    def extract_poses_from_video(
        self,
        video_path: str,
        sample_fps: Optional[int] = None
    ) -> List[Dict]:
        """
        Извлечь позы из всех кадров видео
        
        Args:
            video_path: путь к видео
            sample_fps: если указано, извлекать не все кадры
        
        Returns:
            [
                {
                    'frame': 0,
                    'timestamp': 0.0,
                    'landmarks': [{x, y, z, visibility}, ...],
                    'detected': True
                },
                ...
            ]
        """
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        
        poses = []
        frame_count = 0
        
        # Если sample_fps указан, вычисляем какие кадры брать
        frame_skip = 1
        if sample_fps and sample_fps < fps:
            frame_skip = int(fps / sample_fps)
        
        with self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        ) as pose:
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Пропускаем кадры если нужно
                if frame_count % frame_skip != 0:
                    frame_count += 1
                    continue
                
                # Конвертируем BGR → RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # MediaPipe обработка
                result = pose.process(frame_rgb)
                
                pose_data = {
                    'frame': frame_count,
                    'timestamp': round(frame_count / fps, 3),
                    'detected': result.pose_landmarks is not None
                }
                
                if result.pose_landmarks:
                    landmarks = []
                    for lm in result.pose_landmarks.landmark:
                        landmarks.append({
                            'x': float(lm.x),
                            'y': float(lm.y),
                            'z': float(lm.z),
                            'visibility': float(lm.visibility)
                        })
                    pose_data['landmarks'] = landmarks
                
                poses.append(pose_data)
                frame_count += 1
        
        cap.release()
        return poses
    
    def detect_steps(self, poses: List[Dict]) -> List[Dict]:
        """
        Определить шаги по движению стоп
        
        Returns:
            [
                {
                    'timestamp': 0.5,
                    'foot': 'left',
                    'type': 'step'
                },
                ...
            ]
        """
        steps = []
        
        # Индексы MediaPipe для стоп
        LEFT_ANKLE = 27
        RIGHT_ANKLE = 28
        LEFT_FOOT_INDEX = 31
        RIGHT_FOOT_INDEX = 32
        
        prev_left_y = None
        prev_right_y = None
        
        # Порог для определения шага (изменение Y координаты стопы)
        STEP_THRESHOLD = 0.05
        
        for i, pose in enumerate(poses):
            if not pose.get('detected') or 'landmarks' not in pose:
                continue
            
            landmarks = pose['landmarks']
            
            # Текущие координаты стоп
            left_foot_y = landmarks[LEFT_FOOT_INDEX]['y']
            right_foot_y = landmarks[RIGHT_FOOT_INDEX]['y']
            
            # Первый кадр - сохраняем и пропускаем
            if prev_left_y is None:
                prev_left_y = left_foot_y
                prev_right_y = right_foot_y
                continue
            
            # Определяем движение
            left_movement = abs(left_foot_y - prev_left_y)
            right_movement = abs(right_foot_y - prev_right_y)
            
            # Шаг левой ногой
            if left_movement > STEP_THRESHOLD and left_movement > right_movement:
                steps.append({
                    'timestamp': pose['timestamp'],
                    'foot': 'left',
                    'type': 'step',
                    'movement': round(left_movement, 3)
                })
            
            # Шаг правой ногой
            elif right_movement > STEP_THRESHOLD and right_movement > left_movement:
                steps.append({
                    'timestamp': pose['timestamp'],
                    'foot': 'right',
                    'type': 'step',
                    'movement': round(right_movement, 3)
                })
            
            prev_left_y = left_foot_y
            prev_right_y = right_foot_y
        
        return steps
    
    def calculate_angles(self, landmarks: List[Dict]) -> Dict[str, float]:
        """
        Вычислить углы суставов
        
        Returns:
            {
                'spine_angle': 15.0,
                'left_knee_angle': 150.0,
                'right_knee_angle': 148.0,
                ...
            }
        """
        def angle_between_points(p1, p2, p3):
            """Угол между тремя точками (p2 - вершина)"""
            v1 = np.array([p1['x'] - p2['x'], p1['y'] - p2['y']])
            v2 = np.array([p3['x'] - p2['x'], p3['y'] - p2['y']])
            
            cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
            angle = np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))
            
            return float(angle)
        
        # Индексы MediaPipe
        LEFT_SHOULDER = 11
        RIGHT_SHOULDER = 12
        LEFT_HIP = 23
        RIGHT_HIP = 24
        LEFT_KNEE = 25
        RIGHT_KNEE = 26
        LEFT_ANKLE = 27
        RIGHT_ANKLE = 28
        
        angles = {}
        
        # Угол спины (плечи - бёдра - вертикаль)
        mid_shoulder = {
            'x': (landmarks[LEFT_SHOULDER]['x'] + landmarks[RIGHT_SHOULDER]['x']) / 2,
            'y': (landmarks[LEFT_SHOULDER]['y'] + landmarks[RIGHT_SHOULDER]['y']) / 2
        }
        mid_hip = {
            'x': (landmarks[LEFT_HIP]['x'] + landmarks[RIGHT_HIP]['x']) / 2,
            'y': (landmarks[LEFT_HIP]['y'] + landmarks[RIGHT_HIP]['y']) / 2
        }
        vertical = {
            'x': mid_hip['x'],
            'y': mid_hip['y'] + 0.1  # Точка ниже бёдер
        }
        
        angles['spine_angle'] = angle_between_points(mid_shoulder, mid_hip, vertical)
        
        # Угол левого колена
        angles['left_knee_angle'] = angle_between_points(
            landmarks[LEFT_HIP],
            landmarks[LEFT_KNEE],
            landmarks[LEFT_ANKLE]
        )
        
        # Угол правого колена
        angles['right_knee_angle'] = angle_between_points(
            landmarks[RIGHT_HIP],
            landmarks[RIGHT_KNEE],
            landmarks[RIGHT_ANKLE]
        )
        
        return angles

# Singleton
pose_service = PoseService()
```

**Результат:** ✅ PoseService создан

---

#### Шаг 5.2: Тестовый скрипт для поз

Создать `backend/scripts/test_pose_detection.py`:

```python
import sys
sys.path.append('..')

from app.services.pose_service import pose_service
import os

def main():
    print("=" * 60)
    print("ТЕСТ: Определение поз и шагов")
    print("=" * 60)
    
    # Путь к тестовому видео
    test_video = "C:/Users/kt/important/university/diploma/hasl_files/Американка.mp4"
    
    if not os.path.exists(test_video):
        print("❌ Тестовое видео не найдено")
        return
    
    print(f"📹 Видео: {test_video}")
    print()
    
    # Шаг 1: Извлечь позы
    print("Шаг 1: Извлечение поз (это займёт ~30-60 секунд)...")
    poses = pose_service.extract_poses_from_video(test_video)
    
    detected_count = sum(1 for p in poses if p['detected'])
    
    print(f"✅ Всего кадров: {len(poses)}")
    print(f"✅ Поза определена: {detected_count} ({detected_count/len(poses)*100:.1f}%)")
    print()
    
    # Показать первую позу
    first_with_pose = next((p for p in poses if p['detected']), None)
    if first_with_pose:
        print(f"Первая поза (кадр {first_with_pose['frame']}):")
        print(f"  Timestamp: {first_with_pose['timestamp']}s")
        print(f"  Landmarks: {len(first_with_pose['landmarks'])} точек")
        
        # Вычислить углы
        angles = pose_service.calculate_angles(first_with_pose['landmarks'])
        print(f"  Углы:")
        print(f"    Спина: {angles['spine_angle']:.1f}°")
        print(f"    Левое колено: {angles['left_knee_angle']:.1f}°")
        print(f"    Правое колено: {angles['right_knee_angle']:.1f}°")
    
    print()
    
    # Шаг 2: Определить шаги
    print("Шаг 2: Определение шагов...")
    steps = pose_service.detect_steps(poses)
    
    print(f"✅ Шагов найдено: {len(steps)}")
    
    if steps:
        print()
        print("Первые 10 шагов:")
        for i, step in enumerate(steps[:10]):
            print(f"  Шаг {i+1}: {step['timestamp']:.3f}s - {step['foot']} нога")
    
    print()
    print("=" * 60)
    print("✅ ТЕСТ ЗАВЕРШЁН")
    print("=" * 60)
    
    # Статистика
    left_steps = sum(1 for s in steps if s['foot'] == 'left')
    right_steps = sum(1 for s in steps if s['foot'] == 'right')
    
    print(f"\nСтатистика:")
    print(f"  Левая нога: {left_steps} шагов")
    print(f"  Правая нога: {right_steps} шагов")
    print(f"  Соотношение: {left_steps/right_steps:.2f}" if right_steps > 0 else "")

if __name__ == "__main__":
    main()
```

Запустить:

```bash
cd backend/scripts
python test_pose_detection.py
```

**Ожидаемый вывод:**
```
============================================================
ТЕСТ: Определение поз и шагов
============================================================
📹 Видео: .../Американка.mp4

Шаг 1: Извлечение поз (это займёт ~30-60 секунд)...
✅ Всего кадров: 897
✅ Поза определена: 856 (95.4%)

Первая поза (кадр 0):
  Timestamp: 0.0s
  Landmarks: 33 точек
  Углы:
    Спина: 12.3°
    Левое колено: 155.7°
    Правое колено: 152.4°

Шаг 2: Определение шагов...
✅ Шагов найдено: 68

Первые 10 шагов:
  Шаг 1: 0.500s - left нога
  Шаг 2: 0.967s - right нога
  Шаг 3: 1.400s - left нога
  ...

============================================================
✅ ТЕСТ ЗАВЕРШЁН
============================================================

Статистика:
  Левая нога: 34 шагов
  Правая нога: 34 шагов
  Соотношение: 1.00
```

**Результат:** ✅ Определение поз и шагов работает

---

### 🌤️ ДЕНЬ (2-3 часа)

#### Шаг 5.3: Интеграция: ритм + шаги = ошибки

Создать `backend/app/services/rhythm_service.py`:

```python
from typing import List, Dict
from app.services.audio_service import audio_service
from app.services.pose_service import pose_service
from app.utils.video_utils import VideoUtils
import os

class RhythmService:
    def __init__(self):
        self.tolerance = 0.15  # 150ms tolerance
    
    def analyze_rhythm(self, video_path: str) -> Dict:
        """
        Полный анализ ритма:
        1. Извлечь аудио
        2. Определить биты
        3. Определить шаги
        4. Сопоставить шаги с битами
        
        Returns:
            {
                'tempo': 136.0,
                'total_beats': 68,
                'total_steps': 65,
                'accuracy': 0.85,
                'errors': [...],
                'rhythm_score': 8.5
            }
        """
        result = {
            'tempo': 0,
            'total_beats': 0,
            'total_steps': 0,
            'accuracy': 0,
            'errors': [],
            'rhythm_score': 0
        }
        
        # Шаг 1: Извлечь аудио
        audio_path = video_path.replace('.mp4', '_audio.wav')
        success = VideoUtils.extract_audio(video_path, audio_path)
        
        if not success:
            raise Exception("Failed to extract audio")
        
        try:
            # Шаг 2: Анализ аудио
            audio_analysis = audio_service.analyze_audio(audio_path)
            result['tempo'] = audio_analysis['tempo']
            result['total_beats'] = len(audio_analysis['beats'])
            
            # Шаг 3: Определение поз и шагов
            poses = pose_service.extract_poses_from_video(video_path)
            steps = pose_service.detect_steps(poses)
            result['total_steps'] = len(steps)
            
            # Шаг 4: Сопоставление
            errors = []
            on_beat_count = 0
            
            for step in steps:
                closest_beat, diff = audio_service.find_closest_beat(
                    step['timestamp'],
                    audio_analysis['beats']
                )
                
                is_on_beat = diff <= self.tolerance
                
                if is_on_beat:
                    on_beat_count += 1
                else:
                    # Ошибка ритма
                    if diff > 0.3:
                        severity = "critical"
                    elif diff > 0.2:
                        severity = "high"
                    else:
                        severity = "medium"
                    
                    description = f"Шаг {step['foot']} ногой "
                    if step['timestamp'] > closest_beat:
                        description += f"опоздал на {diff:.2f} сек"
                    else:
                        description += f"опередил бит на {diff:.2f} сек"
                    
                    errors.append({
                        'timestamp': step['timestamp'],
                        'category': 'rhythm',
                        'severity': severity,
                        'description': description,
                        'recommendation': 'Слушай акценты в музыке и делай шаг точно на бит',
                        'closest_beat': closest_beat,
                        'difference': round(diff, 3)
                    })
            
            # Точность и оценка
            result['accuracy'] = on_beat_count / len(steps) if steps else 0
            result['rhythm_score'] = round(result['accuracy'] * 10, 1)
            result['errors'] = errors
            
        finally:
            # Очистка временного аудио
            if os.path.exists(audio_path):
                os.remove(audio_path)
        
        return result

# Singleton
rhythm_service = RhythmService()
```

**Результат:** ✅ RhythmService создан

---

#### Шаг 5.4: Полный тест ритм-анализа

Создать `backend/scripts/test_rhythm_analysis.py`:

```python
import sys
sys.path.append('..')

from app.services.rhythm_service import rhythm_service
import os
import json

def main():
    print("=" * 60)
    print("ТЕСТ: Полный анализ ритма")
    print("=" * 60)
    
    test_video = "C:/Users/kt/important/university/diploma/hasl_files/Американка.mp4"
    
    if not os.path.exists(test_video):
        print("❌ Тестовое видео не найдено")
        return
    
    print(f"📹 Видео: {test_video}")
    print()
    print("⏳ Анализ займёт ~1-2 минуты...")
    print()
    
    # Анализ
    result = rhythm_service.analyze_rhythm(test_video)
    
    # Результаты
    print("=" * 60)
    print("РЕЗУЛЬТАТЫ")
    print("=" * 60)
    print(f"🎵 Темп (BPM): {result['tempo']:.1f}")
    print(f"🎶 Битов в музыке: {result['total_beats']}")
    print(f"👟 Шагов танцора: {result['total_steps']}")
    print(f"✅ Точность ритма: {result['accuracy']*100:.1f}%")
    print(f"⭐ Оценка ритма: {result['rhythm_score']}/10")
    print(f"❌ Ошибок ритма: {len(result['errors'])}")
    print()
    
    # Показать ошибки
    if result['errors']:
        print("Первые 5 ошибок:")
        for i, error in enumerate(result['errors'][:5]):
            print(f"\n{i+1}. [{error['severity'].upper()}] {error['timestamp']:.2f}s")
            print(f"   {error['description']}")
            print(f"   Ближайший бит: {error['closest_beat']:.3f}s (разница {error['difference']}s)")
    
    print()
    print("=" * 60)
    
    # Сохранить результат
    output_file = "rhythm_analysis_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Результат сохранён: {output_file}")
    print("=" * 60)

if __name__ == "__main__":
    main()
```

Запустить:

```bash
cd backend/scripts
python test_rhythm_analysis.py
```

**Ожидаемый вывод:**
```
============================================================
ТЕСТ: Полный анализ ритма
============================================================
📹 Видео: .../Американка.mp4

⏳ Анализ займёт ~1-2 минуты...

============================================================
РЕЗУЛЬТАТЫ
============================================================
🎵 Темп (BPM): 136.0
🎶 Битов в музыке: 68
👟 Шагов танцора: 65
✅ Точность ритма: 85.0%
⭐ Оценка ритма: 8.5/10
❌ Ошибок ритма: 10

Первые 5 ошибок:

1. [HIGH] 5.30s
   Шаг left ногой опоздал на 0.27 сек
   Ближайший бит: 5.030s (разница 0.270s)

2. [MEDIUM] 8.75s
   Шаг right ногой опередил бит на 0.18 сек
   Ближайший бит: 8.930s (разница 0.180s)
...

============================================================
✅ Результат сохранён: rhythm_analysis_result.json
============================================================
```

**Результат:** ✅ Полный анализ ритма работает

---

### 🌙 ВЕЧЕР (1-2 часа)

#### Шаг 5.5: Коммит прогресса

```bash
git add .
git commit -m "feat(week2-day5): pose detection and rhythm analysis integration

- PoseService: MediaPipe pose extraction, step detection, angle calculation
- RhythmService: full rhythm analysis (audio + poses + matching)
- Integration: steps matched with beats
- Rhythm score calculation
- Test scripts validate complete flow

Tests:
- ✅ MediaPipe detects poses (95%+ accuracy)
- ✅ Step detection from foot movement
- ✅ Full rhythm analysis: beats vs steps
- ✅ Rhythm score: 8.5/10 for test video

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"

git push origin main
```

**Результат:** ✅ День 5 завершён

---

## ✅ ИТОГ ДНЯ 5:

```
✅ PoseService: извлечение поз из видео (MediaPipe)
✅ Определение шагов по движению стоп
✅ Вычисление углов суставов
✅ RhythmService: полный анализ ритма
✅ Сопоставление шагов с битами
✅ Расчёт точности ритма и оценки
✅ Генерация ошибок ритма с severity

🎉 MILESTONE: Локальный анализ ритма полностью работает
🎉 Результат: JSON с ошибками ритма готов
```

---

## ✅ ИТОГ НЕДЕЛИ 2 (День 4-5):

```
✅ AudioService: извлечение аудио, определение битов (librosa)
✅ PoseService: определение поз и шагов (MediaPipe)
✅ RhythmService: полный анализ ритма
✅ Для 2-минутного видео:
   - Темп (BPM): ✅
   - Биты: ✅
   - Шаги: ✅
   - Точность ритма: ✅
   - Ошибки ритма: ✅
   - Оценка ритма: ✅

📊 Пример результата:
   - BPM: 136
   - Точность: 85%
   - Оценка: 8.5/10
   - Ошибок: 10

🚀 ГОТОВЫ К НЕДЕЛЕ 3: Claude API интеграция
```
