# 🚀 ПОЛНЫЙ ПЛАН РАЗРАБОТКИ MVP
## Веб-сервис анализа техники танца хастл

**Срок:** 12-13 недель (цель - закончить быстрее)  
**Дата начала:** [указать]  
**Дата защиты:** [указать]

---

## 📋 СОДЕРЖАНИЕ

1. [Неделя 1: Подготовка](#неделя-1-подготовка-4-5-дней)
2. [Неделя 2: Анализ аудио и поз](#неделя-2-анализ-аудио-и-поз-5-дней)
3. [Неделя 3: Claude API и визуализация](#неделя-3-claude-api-и-визуализация-5-дней)
4. [Неделя 4: Интеграция в Celery](#неделя-4-интеграция-в-celery-5-дней)
5. [Неделя 5-6: Frontend Upload и Processing](#неделя-5-6-frontend-upload-и-processing-10-дней)
6. [Неделя 7: Frontend Results](#неделя-7-frontend-results-5-дней)
7. [Неделя 8: Личный кабинет](#неделя-8-личный-кабинет-5-дней)
8. [Неделя 9-10: Полировка и тестирование](#неделя-9-10-полировка-и-тестирование-10-дней)
9. [Неделя 11: Документация](#неделя-11-документация-5-дней)
10. [Неделя 12: Презентация](#неделя-12-презентация-5-дней)
11. [Неделя 13: Резерв и защита](#неделя-13-резерв-и-защита)

---

# 📅 НЕДЕЛЯ 1: ПОДГОТОВКА (4-5 дней)

## Цель недели
Настроить окружение, создать базовую структуру, обработать датасет эталонов, реализовать Auth.

---

## День 1: Инфраструктура и датасет

### Утро (2-3 часа)

**1.1. Git репозиторий**
```bash
mkdir hustl-analyzer
cd hustl-analyzer
git init
git remote add origin https://github.com/YOUR_USERNAME/hustl-analyzer.git

# .gitignore
cat > .gitignore << 'EOF'
# Python
venv/
__pycache__/
*.pyc
.env

# Node
node_modules/
dist/

# Data
backend/data/uploads/
backend/data/reference_poses/*.json

# IDE
.DS_Store
.vscode/
.idea/
EOF
```

**1.2. Структура проекта**
```bash
# Backend
mkdir -p backend/app/{api,models,services,tasks,core,db,schemas,utils}
mkdir -p backend/data/{reference_poses,uploads/temp,uploads/saved}
mkdir -p backend/scripts
mkdir -p backend/tests

# Frontend
mkdir -p frontend/src/{pages,components,services,hooks,types,utils}
mkdir -p frontend/public

# Docs
mkdir docs

# Python packages
touch backend/app/__init__.py
touch backend/app/{api,models,services,tasks,core,db,schemas,utils}/__init__.py
```

**1.3. Скрипт обработки датасета**

Создать `backend/scripts/extract_all_references.py`:

```python
import os
import cv2
import json
import mediapipe as mp
from pathlib import Path
from tqdm import tqdm
from datetime import datetime

DATASET_PATH = "C:/Users/kt/important/university/diploma/hasl_files"
OUTPUT_PATH = "../data/reference_poses"

mp_pose = mp.solutions.pose

def extract_element_name(filename):
    return Path(filename).stem

def process_video(video_path, element_name):
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
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = pose.process(frame_rgb)
            
            if result.pose_landmarks:
                landmarks = [
                    {
                        "x": float(lm.x),
                        "y": float(lm.y),
                        "z": float(lm.z),
                        "visibility": float(lm.visibility)
                    }
                    for lm in result.pose_landmarks.landmark
                ]
                
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
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    output_file = os.path.join(OUTPUT_PATH, f"{element_name}.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    print("=" * 60)
    print("🎬 ОБРАБОТКА ДАТАСЕТА ЭТАЛОННЫХ ВИДЕО")
    print("=" * 60)
    print(f"📁 Датасет: {DATASET_PATH}")
    print(f"💾 Результат: {OUTPUT_PATH}")
    print()
    
    if not os.path.exists(DATASET_PATH):
        print(f"❌ Датасет не найден: {DATASET_PATH}")
        return
    
    video_files = [
        f for f in os.listdir(DATASET_PATH)
        if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))
    ]
    
    if not video_files:
        print("❌ Видео не найдены")
        return
    
    print(f"📊 Найдено видео: {len(video_files)}")
    print(f"⏱️  Время: CPU ~5-7 часов, GPU ~1-2 часа")
    print()
    input("Нажмите Enter для начала...")
    print()
    
    start_time = datetime.now()
    success_count = 0
    error_count = 0
    
    for video_file in tqdm(video_files, desc="🎬 Обработка", unit="видео"):
        element_name = extract_element_name(video_file)
        video_path = os.path.join(DATASET_PATH, video_file)
        
        # Пропуск обработанных
        output_file = os.path.join(OUTPUT_PATH, f"{element_name}.json")
        if os.path.exists(output_file):
            tqdm.write(f"⏭️  {element_name}: уже обработан")
            success_count += 1
            continue
        
        try:
            data = process_video(video_path, element_name)
            save_reference(data, element_name)
            
            tqdm.write(
                f"✅ {element_name}: "
                f"{data['poses_count']} поз из {data['total_frames']} кадров"
            )
            success_count += 1
            
        except Exception as e:
            tqdm.write(f"❌ {video_file}: {e}")
            error_count += 1
            
            with open("errors.log", "a", encoding="utf-8") as log:
                log.write(f"{datetime.now().isoformat()} | {video_file} | {e}\n")
    
    duration = datetime.now() - start_time
    
    print()
    print("=" * 60)
    print("🎉 ОБРАБОТКА ЗАВЕРШЕНА!")
    print("=" * 60)
    print(f"✅ Успешно: {success_count}")
    print(f"❌ Ошибок: {error_count}")
    print(f"⏱️  Время: {duration}")
    print(f"💾 Сохранено в: {OUTPUT_PATH}")
    print("=" * 60)

if __name__ == "__main__":
    main()
```

**1.4. Запустить обработку (В ФОНЕ!)**
```bash
cd backend/scripts
pip install opencv-python mediapipe tqdm
python extract_all_references.py
# Идёт 5-7 часов - займёмся другим
```

---

### День (пока обработка идёт, 3-4 часа)

**1.5. Backend зависимости**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

cat > requirements.txt << 'EOF'
# Web
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
ffmpeg-python==0.2.0
EOF

pip install -r requirements.txt
```

**1.6. Frontend зависимости**
```bash
cd ../frontend
npm create vite@latest . -- --template react-ts

npm install @mui/material @emotion/react @emotion/styled
npm install @mui/icons-material
npm install axios react-router-dom recharts react-player react-toastify
npm install --save-dev @types/node
```

**1.7. Docker Compose**
```bash
cd ..
cat > docker-compose.yml << 'EOF'
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
EOF

docker-compose up -d
docker-compose ps
```

---

### Вечер (2 часа)

**1.8. Коммит**
```bash
git add .
git commit -m "feat: initial setup

- Project structure
- Dependencies (Python, Node)
- Docker Compose (PostgreSQL, Redis)
- Dataset processing script started

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin main
```

**✅ Итог дня 1:**
- ✅ Репозиторий создан
- ✅ Структура готова
- ✅ Зависимости установлены
- ✅ Docker работает
- ⏳ Датасет обрабатывается (5-7 часов)

---

## День 2: Backend Core - Database & Auth

### Утро (3-4 часа)

**2.1. Конфигурация**

`backend/.env`:
```env
DATABASE_URL=postgresql://hustl_user:hustl_pass_2026@localhost:5432/hustl_db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-super-secret-key-change-in-production-min-32-chars
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
UPLOAD_DIR=data/uploads
MAX_FILE_SIZE=1073741824
MAX_VIDEO_DURATION=600
```

`backend/app/config.py`:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ANTHROPIC_API_KEY: str
    UPLOAD_DIR: str = "data/uploads"
    MAX_FILE_SIZE: int = 1073741824
    MAX_VIDEO_DURATION: int = 600
    ALLOWED_VIDEO_FORMATS: list = [".mp4", ".avi", ".mov", ".mkv"]
    CORS_ORIGINS: list = ["http://localhost:3000"]
    
    class Config:
        env_file = ".env"

settings = Settings()
```

**2.2. Database session**

`backend/app/db/session.py`:
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**2.3. Модели БД**

`backend/app/models/user.py`:
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
    
    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")
    temp_uploads = relationship("TempUpload", back_populates="user", cascade="all, delete-orphan")
```

`backend/app/models/video.py`:
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
    
    user = relationship("User", back_populates="videos")
    analyses = relationship("Analysis", back_populates="video", cascade="all, delete-orphan")
```

`backend/app/models/analysis.py`:
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
    overall_score = Column(Float)
    rhythm_score = Column(Float)
    posture_score = Column(Float)
    technique_score = Column(Float)
    musicality_score = Column(Float)
    total_errors = Column(Integer, default=0)
    ai_response = Column(JSON)
    processing_time = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    
    video = relationship("Video", back_populates="analyses")
    errors = relationship("Error", back_populates="analysis", cascade="all, delete-orphan")
```

`backend/app/models/error.py`:
```python
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base

class Error(Base):
    __tablename__ = "errors"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(Float, nullable=False)
    category = Column(String(20), nullable=False, index=True)
    severity = Column(String(20), nullable=False)
    title = Column(String(255))
    description = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    screenshot_path = Column(Text)  # ← ОДИН композитный скриншот (красный + зелёный)
    detected_element = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    analysis = relationship("Analysis", back_populates="errors")
```

`backend/app/models/temp_upload.py`:
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
    
    user = relationship("User", back_populates="temp_uploads")
```

`backend/app/models/__init__.py`:
```python
from app.db.session import Base
from app.models.user import User
from app.models.video import Video
from app.models.analysis import Analysis
from app.models.error import Error
from app.models.temp_upload import TempUpload

__all__ = ["Base", "User", "Video", "Analysis", "Error", "TempUpload"]
```

**2.4. Миграции**
```bash
cd backend
alembic init alembic

# Отредактировать alembic/env.py:
# from app.db.session import Base
# from app.models import *
# from app.config import settings
# config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
# target_metadata = Base.metadata

alembic revision --autogenerate -m "Initial models"
alembic upgrade head

# Проверка
docker exec -it hustl_postgres psql -U hustl_user -d hustl_db -c "\dt"
```

---

### День (2-3 часа)

**2.5. Auth API**

`backend/app/core/security.py`:
```python
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str):
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
```

`backend/app/schemas/user.py`:
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

`backend/app/api/deps.py`:
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
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

`backend/app/api/auth.py`:
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
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
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
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}
```

`backend/app/api/users.py`:
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
def update_me(user_update: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user_update.name is not None:
        current_user.name = user_update.name
    if user_update.avatar_url is not None:
        current_user.avatar_url = user_update.avatar_url
    
    db.commit()
    db.refresh(current_user)
    return current_user
```

`backend/app/main.py`:
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Hustl Analyzer API", "version": "1.0.0", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```

Запустить:
```bash
cd backend
python -m app.main
# http://localhost:8000/docs
```

---

### Вечер (2 часа)

**2.6. Frontend Auth**

`frontend/src/services/api.ts`:
```typescript
import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

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

`frontend/src/services/authService.ts`:
```typescript
import api from './api'

export interface User {
  id: number
  email: string
  name?: string
  avatar_url?: string
  created_at: string
}

export const authService = {
  async register(data: { email: string; password: string; name?: string }): Promise<User> {
    const response = await api.post('/auth/register', data)
    return response.data
  },

  async login(data: { email: string; password: string }): Promise<string> {
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

`frontend/src/pages/LoginPage.tsx`:
```typescript
import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Container, Paper, TextField, Button, Typography, Box, Alert, Link as MuiLink,
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

          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              margin="normal"
              required
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

`frontend/src/pages/RegisterPage.tsx` - аналогично

`frontend/src/App.tsx`:
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
      <Route path="/upload" element={<PrivateRoute><UploadPage /></PrivateRoute>} />
      <Route path="/" element={<Navigate to="/login" />} />
    </Routes>
  )
}

export default App
```

Запустить:
```bash
cd frontend
npm run dev
# http://localhost:3000
```

**✅ Итог дня 2:**
- ✅ БД модели созданы
- ✅ Auth API работает
- ✅ Frontend Auth UI работает
- ✅ Можно зарегистрироваться и войти

---

## День 3: Проверка датасета + ReferenceService

*(Продолжение в следующем сообщении из-за лимита длины)*

**✅ Итог недели 1:**
```
✅ Backend работает (FastAPI + PostgreSQL + Auth)
✅ Frontend работает (React + MUI + Auth)
✅ Датасет обработан (520 эталонов)
✅ Можно зарегистрироваться и войти через UI

🎉 ГОТОВЫ К РАЗРАБОТКЕ АНАЛИЗА ВИДЕО
```

---

# 📅 НЕДЕЛЯ 2: АНАЛИЗ ВИДЕО - ЛОКАЛЬНЫЙ РИТМ (5 дней)

## Цель недели
Реализовать локальный анализ ритма: извлечение аудио, определение битов, определение поз и шагов, сопоставление с музыкой.

---

## День 4: Анализ аудио + определение битов

### Утро (3-4 часа)

**4.1. Установить FFmpeg**
```bash
# Windows: https://www.gyan.dev/ffmpeg/builds/
# Linux: sudo apt install ffmpeg
# Mac: brew install ffmpeg
ffmpeg -version
```

**4.2. VideoUtils**

`backend/app/utils/video_utils.py`:
```python
import subprocess
import os
import json
from typing import Dict, Optional

class VideoUtils:
    @staticmethod
    def extract_audio(video_path: str, output_path: str) -> bool:
        try:
            cmd = [
                'ffmpeg', '-i', video_path, '-vn',
                '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2',
                '-y', output_path
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return os.path.exists(output_path)
        except subprocess.CalledProcessError:
            return False
    
    @staticmethod
    def get_video_info(video_path: str) -> Optional[Dict]:
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', video_path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            data = json.loads(result.stdout.decode())
            
            video_stream = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
            if not video_stream:
                return None
            
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
        except Exception:
            return None
    
    @staticmethod
    def extract_frame(video_path: str, timestamp: float, output_path: str) -> bool:
        try:
            cmd = ['ffmpeg', '-ss', str(timestamp), '-i', video_path, '-vframes', '1', '-y', output_path]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return os.path.exists(output_path)
        except subprocess.CalledProcessError:
            return False
```

**4.3. AudioService**

`backend/app/services/audio_service.py`:
```python
import librosa
import numpy as np
from typing import List, Dict, Tuple

class AudioService:
    def analyze_audio(self, audio_path: str) -> Dict:
        y, sr = librosa.load(audio_path, sr=None)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units='frames')
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        duration = librosa.get_duration(y=y, sr=sr)
        
        return {
            'tempo': float(tempo),
            'beats': beat_times.tolist(),
            'beat_frames': beat_frames.tolist(),
            'duration': float(duration),
            'sample_rate': int(sr)
        }
    
    def find_closest_beat(self, timestamp: float, beats: List[float]) -> Tuple[float, float]:
        if not beats:
            return (0.0, float('inf'))
        
        beats_array = np.array(beats)
        differences = np.abs(beats_array - timestamp)
        closest_idx = np.argmin(differences)
        
        return (float(beats_array[closest_idx]), float(differences[closest_idx]))
    
    def is_on_beat(self, timestamp: float, beats: List[float], tolerance: float = 0.15) -> bool:
        _, diff = self.find_closest_beat(timestamp, beats)
        return diff <= tolerance

audio_service = AudioService()
```

**4.4. Тест**

`backend/scripts/test_audio_analysis.py` - создать тестовый скрипт и запустить.

**✅ Итог дня 4:**
- ✅ FFmpeg работает
- ✅ VideoUtils: извлечение аудио
- ✅ AudioService: определение битов
- ✅ Тест пройден

---

## День 5: MediaPipe - определение поз и шагов

### Утро (3-4 часа)

**5.1. PoseService**

`backend/app/services/pose_service.py`:
```python
import cv2
import mediapipe as mp
import numpy as np
from typing import List, Dict, Optional

class PoseService:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
    
    def extract_poses_from_video(self, video_path: str, sample_fps: Optional[int] = None) -> List[Dict]:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        poses = []
        frame_count = 0
        frame_skip = 1
        
        if sample_fps and sample_fps < fps:
            frame_skip = int(fps / sample_fps)
        
        with self.mp_pose.Pose(static_image_mode=False, model_complexity=1) as pose:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_count % frame_skip != 0:
                    frame_count += 1
                    continue
                
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = pose.process(frame_rgb)
                
                pose_data = {
                    'frame': frame_count,
                    'timestamp': round(frame_count / fps, 3),
                    'detected': result.pose_landmarks is not None
                }
                
                if result.pose_landmarks:
                    landmarks = [
                        {'x': float(lm.x), 'y': float(lm.y), 'z': float(lm.z), 'visibility': float(lm.visibility)}
                        for lm in result.pose_landmarks.landmark
                    ]
                    pose_data['landmarks'] = landmarks
                
                poses.append(pose_data)
                frame_count += 1
        
        cap.release()
        return poses
    
    def detect_steps(self, poses: List[Dict]) -> List[Dict]:
        steps = []
        LEFT_FOOT_INDEX = 31
        RIGHT_FOOT_INDEX = 32
        STEP_THRESHOLD = 0.05
        
        prev_left_y = None
        prev_right_y = None
        
        for pose in poses:
            if not pose.get('detected') or 'landmarks' not in pose:
                continue
            
            landmarks = pose['landmarks']
            left_foot_y = landmarks[LEFT_FOOT_INDEX]['y']
            right_foot_y = landmarks[RIGHT_FOOT_INDEX]['y']
            
            if prev_left_y is None:
                prev_left_y = left_foot_y
                prev_right_y = right_foot_y
                continue
            
            left_movement = abs(left_foot_y - prev_left_y)
            right_movement = abs(right_foot_y - prev_right_y)
            
            if left_movement > STEP_THRESHOLD and left_movement > right_movement:
                steps.append({'timestamp': pose['timestamp'], 'foot': 'left', 'type': 'step'})
            elif right_movement > STEP_THRESHOLD and right_movement > left_movement:
                steps.append({'timestamp': pose['timestamp'], 'foot': 'right', 'type': 'step'})
            
            prev_left_y = left_foot_y
            prev_right_y = right_foot_y
        
        return steps
    
    def calculate_angles(self, landmarks: List[Dict]) -> Dict[str, float]:
        def angle_between_points(p1, p2, p3):
            v1 = np.array([p1['x'] - p2['x'], p1['y'] - p2['y']])
            v2 = np.array([p3['x'] - p2['x'], p3['y'] - p2['y']])
            cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
            return float(np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0))))
        
        mid_shoulder = {'x': (landmarks[11]['x'] + landmarks[12]['x']) / 2, 'y': (landmarks[11]['y'] + landmarks[12]['y']) / 2}
        mid_hip = {'x': (landmarks[23]['x'] + landmarks[24]['x']) / 2, 'y': (landmarks[23]['y'] + landmarks[24]['y']) / 2}
        vertical = {'x': mid_hip['x'], 'y': mid_hip['y'] + 0.1}
        
        return {
            'spine_angle': angle_between_points(mid_shoulder, mid_hip, vertical),
            'left_knee_angle': angle_between_points(landmarks[23], landmarks[25], landmarks[27]),
            'right_knee_angle': angle_between_points(landmarks[24], landmarks[26], landmarks[28])
        }

pose_service = PoseService()
```

**5.2. RhythmService - интеграция**

`backend/app/services/rhythm_service.py`:
```python
from typing import Dict
from app.services.audio_service import audio_service
from app.services.pose_service import pose_service
from app.utils.video_utils import VideoUtils
import os

class RhythmService:
    def __init__(self):
        self.tolerance = 0.15
    
    def analyze_rhythm(self, video_path: str) -> Dict:
        result = {'tempo': 0, 'total_beats': 0, 'total_steps': 0, 'accuracy': 0, 'errors': [], 'rhythm_score': 0}
        
        audio_path = video_path.replace('.mp4', '_audio.wav')
        success = VideoUtils.extract_audio(video_path, audio_path)
        if not success:
            raise Exception("Failed to extract audio")
        
        try:
            audio_analysis = audio_service.analyze_audio(audio_path)
            result['tempo'] = audio_analysis['tempo']
            result['total_beats'] = len(audio_analysis['beats'])
            
            poses = pose_service.extract_poses_from_video(video_path)
            steps = pose_service.detect_steps(poses)
            result['total_steps'] = len(steps)
            
            errors = []
            on_beat_count = 0
            
            for step in steps:
                closest_beat, diff = audio_service.find_closest_beat(step['timestamp'], audio_analysis['beats'])
                is_on_beat = diff <= self.tolerance
                
                if is_on_beat:
                    on_beat_count += 1
                else:
                    severity = "critical" if diff > 0.3 else ("high" if diff > 0.2 else "medium")
                    description = f"Шаг {step['foot']} ногой "
                    description += f"опоздал на {diff:.2f} сек" if step['timestamp'] > closest_beat else f"опередил бит на {diff:.2f} сек"
                    
                    errors.append({
                        'timestamp': step['timestamp'],
                        'category': 'rhythm',
                        'severity': severity,
                        'description': description,
                        'recommendation': 'Слушай акценты в музыке и делай шаг точно на бит',
                        'closest_beat': closest_beat,
                        'difference': round(diff, 3)
                    })
            
            result['accuracy'] = on_beat_count / len(steps) if steps else 0
            result['rhythm_score'] = round(result['accuracy'] * 10, 1)
            result['errors'] = errors
            
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)
        
        return result

rhythm_service = RhythmService()
```

**5.3. Тест**

`backend/scripts/test_rhythm_analysis.py` - создать и запустить полный тест.

**✅ Итог дня 5:**
- ✅ PoseService: определение поз
- ✅ Определение шагов
- ✅ RhythmService: полный анализ ритма
- ✅ JSON с ошибками ритма готов

---

**✅ Итог недели 2:**
```
✅ Локальный анализ ритма полностью работает
✅ AudioService: биты музыки
✅ PoseService: позы и шаги
✅ RhythmService: сопоставление, оценка
✅ Результат: JSON с ошибками ритма

🎉 ГОТОВЫ К CLAUDE API
```

---

# 📅 НЕДЕЛЯ 3: CLAUDE API И ВИЗУАЛИЗАЦИЯ (5 дней)

## Цель недели
Интеграция Claude Opus 5.5 для анализа постуры/техники/музыкальности, распознавание элементов, генерация скриншотов с разметкой.

---

## День 6: Claude API + промпт

### Утро (3-4 часа)

**6.1. ClaudeService**

`backend/app/services/claude_service.py`:
```python
import anthropic
from typing import List, Dict
import base64
from app.config import settings

class ClaudeService:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-opus-5-5-20250514"
    
    def analyze_video(self, frames: List[bytes], rhythm_errors: List[Dict]) -> Dict:
        # Промпт
        prompt = self._build_prompt(rhythm_errors)
        
        # Подготовка изображений
        images = []
        for i, frame_bytes in enumerate(frames[:100]):  # Максимум 100 кадров
            base64_image = base64.b64encode(frame_bytes).decode('utf-8')
            images.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64_image
                }
            })
        
        # Запрос
        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    *images
                ]
            }]
        )
        
        # Парсинг ответа
        response_text = message.content[0].text
        
        # Извлечь JSON из ответа
        import json
        import re
        
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = {"errors": []}
        
        return result
    
    def _build_prompt(self, rhythm_errors: List[Dict]) -> str:
        prompt = """Проанализируй видео танца хастл по 100 ключевым кадрам.

ВАЖНО: Локальный анализ уже нашёл ошибки ритма (см. ниже).
Учитывай их при анализе постуры и техники.

ОШИБКИ РИТМА:
"""
        
        for err in rhythm_errors[:10]:  # Первые 10
            prompt += f"- {err['timestamp']:.1f}s: {err['description']}\n"
        
        prompt += """

ТВОЯ ЗАДАЧА:

1. ПОСТУРА
   - Ровная ли спина (должна быть под углом 10-20°)
   - Положение плеч (не зажаты, на одном уровне)
   - Положение головы (смотрит вперёд, не опущена)
   - Корпус не наклонён вперёд/назад

2. ТЕХНИКА
   - Распознай элементы хастла (Американка, Солнышко, Катапульта, Йoyo, Окошко, etc)
   - Правильность выполнения элементов
   - Координация рук и ног
   - Плавность движений

3. МУЗЫКАЛЬНОСТЬ
   - Соответствие движений характеру музыки
   - Акценты на смену фраз
   - Динамика (контраст быстрых/медленных движений)

4. КОНТЕКСТ
   - Если на тех же таймкодах, где сбился ритм, есть ошибки постуры/техники,
     укажи возможную связь в recommendation

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
      "description": "Корпус наклонён вперёд на 30-35°. Норма: 10-20°.",
      "recommendation": "Выпрями спину, подтяни живот, смотри вперёд."
    }
  ]
}

КРИТЕРИИ severity:
- critical: грубая ошибка, влияет на безопасность или базовую технику
- high: значительная ошибка, портит впечатление
- medium: заметная, но не критичная
- low: мелкая деталь

Верни ТОЛЬКО JSON, без дополнительного текста.
"""
        
        return prompt

claude_service = ClaudeService()
```

**6.2. Извлечение ключевых кадров**

`backend/app/utils/frame_extractor.py`:
```python
import cv2
from typing import List
import numpy as np

class FrameExtractor:
    @staticmethod
    def extract_key_frames(video_path: str, num_frames: int = 100) -> List[bytes]:
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if total_frames == 0:
            return []
        
        # Равномерно распределённые кадры
        frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
        
        frames = []
        current_frame = 0
        
        for target_index in frame_indices:
            # Перемотка к нужному кадру
            if target_index < current_frame:
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_index)
                current_frame = target_index
            else:
                while current_frame < target_index:
                    cap.read()
                    current_frame += 1
            
            ret, frame = cap.read()
            if ret:
                # Конвертировать в JPEG bytes
                _, buffer = cv2.imencode('.jpg', frame)
                frames.append(buffer.tobytes())
        
        cap.release()
        return frames

frame_extractor = FrameExtractor()
```

**6.3. Тест Claude API**

`backend/scripts/test_claude_analysis.py`:
```python
import sys
sys.path.append('..')

from app.services.claude_service import claude_service
from app.utils.frame_extractor import frame_extractor
import json

def main():
    print("=" * 60)
    print("ТЕСТ: Claude API анализ")
    print("=" * 60)
    
    test_video = "C:/Users/kt/important/university/diploma/hasl_files/Американка.mp4"
    
    print(f"📹 Видео: {test_video}")
    print()
    print("⏳ Извлечение кадров...")
    
    frames = frame_extractor.extract_key_frames(test_video, num_frames=100)
    print(f"✅ Извлечено кадров: {len(frames)}")
    print()
    
    print("⏳ Отправка в Claude API (это займёт ~30-60 сек)...")
    
    # Симуляция ошибок ритма
    rhythm_errors = [
        {"timestamp": 5.3, "description": "Шаг left ногой опоздал на 0.27 сек"},
        {"timestamp": 8.8, "description": "Шаг right ногой опередил на 0.18 сек"}
    ]
    
    result = claude_service.analyze_video(frames, rhythm_errors)
    
    print("=" * 60)
    print("РЕЗУЛЬТАТЫ")
    print("=" * 60)
    print(f"⭐ Оценка постуры: {result.get('posture_score', 0)}/10")
    print(f"⭐ Оценка техники: {result.get('technique_score', 0)}/10")
    print(f"⭐ Оценка музыкальности: {result.get('musicality_score', 0)}/10")
    print(f"❌ Ошибок найдено: {len(result.get('errors', []))}")
    print()
    
    # Первые 3 ошибки
    for i, error in enumerate(result.get('errors', [])[:3]):
        print(f"{i+1}. [{error['severity'].upper()}] {error['timestamp']}s - {error['category']}")
        print(f"   Элемент: {error.get('detected_element', 'N/A')}")
        print(f"   {error['description']}")
        print()
    
    # Сохранить
    with open("claude_analysis_result.json", 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("✅ Результат сохранён: claude_analysis_result.json")
    print("=" * 60)

if __name__ == "__main__":
    main()
```

**✅ Итог дня 6:**
- ✅ ClaudeService создан
- ✅ Промпт с описанием элементов
- ✅ Извлечение 100 ключевых кадров
- ✅ Claude API работает

---

## День 7-8: Распознавание элементов + визуализация

*(Детали визуализации: рисование скелетов, стрелок, генерация скриншотов)*

**✅ Итог дня 7-8:**
- ✅ Распознавание элементов (гибрид Claude + MediaPipe)
- ✅ VisualizationService: рисование красного/зелёного скелета
- ✅ Генерация скриншотов с разметкой

---

**✅ Итог недели 3:**
```
✅ Claude API интегрирован
✅ Анализ постуры/техники/музыкальности
✅ Распознавание элементов хастла
✅ Скриншоты с красным/зелёным скелетом
✅ JSON с полным анализом готов

🎉 ГОТОВЫ К ИНТЕГРАЦИИ В CELERY
```

---

# 📅 НЕДЕЛЯ 4: ИНТЕГРАЦИЯ В CELERY (5 дней)

## Цель недели
Объединить все сервисы в Celery задачу, реализовать API endpoints для загрузки видео и получения результатов.

---

## День 9-10: Celery task + API endpoints

**9.1. Celery setup**

`backend/app/core/celery_app.py`:
```python
from celery import Celery
from app.config import settings

celery_app = Celery(
    "hustl_analyzer",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)
```

**9.2. process_video_task (ИСПРАВЛЕННАЯ ВЕРСИЯ)**

`backend/app/tasks/video_tasks.py`:
```python
from celery import Task
from app.core.celery_app import celery_app
from app.services.rhythm_service import rhythm_service
from app.services.claude_service import claude_service
from app.services.visualization_service import visualization_service  # ← ДОБАВЛЕНО
from app.utils.frame_extractor import frame_extractor
from app.db.session import SessionLocal
from app.models.analysis import Analysis
from app.models.error import Error
import time

@celery_app.task(bind=True)
def process_video_task(self: Task, video_id: int, video_path: str):
    db = SessionLocal()
    
    try:
        # Обновить статус
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
        all_errors.sort(key=lambda e: {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(e['severity'], 3))
        top_10_errors = all_errors[:10]
        
        # ШАГ 6: ГЕНЕРАЦИЯ СКРИНШОТОВ ДЛЯ ТОП-10 ОШИБОК ← КРИТИЧНО!
        for err_data in top_10_errors:
            try:
                screenshot_path = visualization_service.create_error_screenshot(
                    video_path=video_path,
                    timestamp=err_data['timestamp'],
                    error_data=err_data,
                    detected_element=err_data.get('detected_element')
                )
                err_data['screenshot_path'] = screenshot_path
            except Exception as e:
                print(f"Error creating screenshot: {e}")
                err_data['screenshot_path'] = None
        
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

**9.3. API для загрузки и управления видео (ИСПРАВЛЕННАЯ ВЕРСИЯ)**

`backend/app/api/videos.py`:
```python
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.video import Video
from app.models.analysis import Analysis
from app.models.temp_upload import TempUpload
from app.tasks.video_tasks import process_video_task
from app.utils.video_utils import VideoUtils
from app.config import settings
import os
import shutil
from datetime import datetime, timedelta
import uuid

router = APIRouter(prefix="/videos", tags=["videos"])

@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Валидация
    if file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 1GB)")
    
    # Сохранить файл
    filename = f"{uuid.uuid4()}_{file.filename}"
    upload_path = os.path.join(settings.UPLOAD_DIR, "temp", filename)
    os.makedirs(os.path.dirname(upload_path), exist_ok=True)
    
    with open(upload_path, "wb") as f:
        f.write(await file.read())
    
    # Получить метаданные
    info = VideoUtils.get_video_info(upload_path)
    if not info:
        os.remove(upload_path)
        raise HTTPException(status_code=400, detail="Invalid video file")
    
    if info['duration'] > settings.MAX_VIDEO_DURATION:
        os.remove(upload_path)
        raise HTTPException(status_code=400, detail="Video too long (max 10 minutes)")
    
    # Создать запись Video
    video = Video(
        user_id=current_user.id,
        original_filename=file.filename,
        file_path=upload_path,
        duration=info['duration'],
        size=info['size'],
        resolution=f"{info['width']}x{info['height']}",
        fps=int(info['fps']),
        format=info['codec'],
        is_saved=False
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    
    # Создать TempUpload (истекает через 24 часа)
    temp_upload = TempUpload(
        user_id=current_user.id,
        file_path=upload_path,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.add(temp_upload)
    db.commit()
    
    # Создать Analysis
    analysis = Analysis(video_id=video.id, status="queued")
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    
    # Запустить Celery задачу
    process_video_task.delay(video.id, upload_path)
    
    return {
        "video_id": video.id,
        "analysis_id": analysis.id,
        "status": "queued",
        "message": "Video uploaded successfully. Processing started."
    }

@router.get("/analysis/{analysis_id}")
def get_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Проверка доступа
    if analysis.video.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "id": analysis.id,
        "video_id": analysis.video_id,
        "status": analysis.status,
        "overall_score": analysis.overall_score,
        "rhythm_score": analysis.rhythm_score,
        "posture_score": analysis.posture_score,
        "technique_score": analysis.technique_score,
        "musicality_score": analysis.musicality_score,
        "total_errors": analysis.total_errors,
        "processing_time": analysis.processing_time,
        "created_at": analysis.created_at,
        "completed_at": analysis.completed_at,
        "error_message": analysis.error_message,
        "errors": [
            {
                "id": err.id,
                "timestamp": err.timestamp,
                "category": err.category,
                "severity": err.severity,
                "title": err.title,
                "description": err.description,
                "recommendation": err.recommendation,
                "screenshot_path": err.screenshot_path,
                "detected_element": err.detected_element
            }
            for err in analysis.errors
        ]
    }

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
    
    if video.is_saved:
        return {"status": "already_saved", "video_id": video.id}
    
    # Переместить файл
    old_path = video.file_path
    new_filename = os.path.basename(old_path)
    new_path = os.path.join(settings.UPLOAD_DIR, "saved", new_filename)
    
    os.makedirs(os.path.dirname(new_path), exist_ok=True)
    
    if os.path.exists(old_path):
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
    
    # Удалить из TempUploads (если есть)
    temp_upload = db.query(TempUpload).filter(
        TempUpload.file_path == video.file_path
    ).first()
    if temp_upload:
        db.delete(temp_upload)
    
    # Удалить из БД (каскадное удаление Video → Analysis → Errors)
    db.delete(video)
    db.commit()
    
    return {"status": "deleted", "message": "Analysis and video deleted successfully"}

@router.get("/history")
def get_video_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0
):
    """
    Получить историю сохранённых анализов
    """
    videos = db.query(Video).filter(
        Video.user_id == current_user.id,
        Video.is_saved == True
    ).order_by(Video.uploaded_at.desc()).limit(limit).offset(offset).all()
    
    return {
        "videos": [
            {
                "id": v.id,
                "original_filename": v.original_filename,
                "duration": v.duration,
                "uploaded_at": v.uploaded_at,
                "thumbnail_path": v.thumbnail_path,
                "analysis": {
                    "id": v.analyses[0].id if v.analyses else None,
                    "overall_score": v.analyses[0].overall_score if v.analyses else None,
                    "total_errors": v.analyses[0].total_errors if v.analyses else None
                } if v.analyses else None
            }
            for v in videos
        ],
        "total": db.query(Video).filter(
            Video.user_id == current_user.id,
            Video.is_saved == True
        ).count()
    }
```

**✅ Итог дня 9-10:**
- ✅ Celery настроен
- ✅ process_video_task объединяет все сервисы
- ✅ API upload работает
- ✅ API get_analysis работает
- ✅ API save/discard работает
- ✅ Очистка временных файлов настроена

---

## День 10 (вечер): Celery задача очистки временных файлов

**10.1. Периодическая задача очистки**

`backend/app/tasks/cleanup_tasks.py`:
```python
from celery import Task
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.temp_upload import TempUpload
from datetime import datetime
import os

@celery_app.task
def cleanup_expired_uploads():
    """
    Периодическая задача (каждый час):
    Удаляет истёкшие временные файлы
    """
    db = SessionLocal()
    
    try:
        # Найти истёкшие
        expired = db.query(TempUpload).filter(
            TempUpload.expires_at < datetime.utcnow()
        ).all()
        
        deleted_count = 0
        
        for temp in expired:
            # Удалить файл
            if os.path.exists(temp.file_path):
                try:
                    os.remove(temp.file_path)
                    deleted_count += 1
                except Exception as e:
                    print(f"Error deleting file {temp.file_path}: {e}")
            
            # Удалить запись
            db.delete(temp)
        
        db.commit()
        
        return {"deleted": deleted_count, "message": f"Cleaned up {deleted_count} expired files"}
        
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()
```

**10.2. Настройка периодического запуска**

`backend/app/core/celery_app.py`:
```python
from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "hustl_analyzer",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Настройка периодических задач
celery_app.conf.beat_schedule = {
    'cleanup-expired-uploads': {
        'task': 'app.tasks.cleanup_tasks.cleanup_expired_uploads',
        'schedule': crontab(minute=0),  # Каждый час в 00 минут
    },
}

celery_app.conf.timezone = 'UTC'
```

**10.3. Запуск Celery Beat**

```bash
# Запустить worker
celery -A app.core.celery_app worker --loglevel=info

# Запустить beat (планировщик) в отдельном терминале
celery -A app.core.celery_app beat --loglevel=info
```

**10.4. Docker Compose для Celery (опционально)**

Добавить в `docker-compose.yml`:
```yaml
  celery_worker:
    build: ./backend
    command: celery -A app.core.celery_app worker --loglevel=info
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend:/app
    environment:
      - DATABASE_URL=postgresql://hustl_user:hustl_pass_2026@postgres:5432/hustl_db
      - REDIS_URL=redis://redis:6379/0

  celery_beat:
    build: ./backend
    command: celery -A app.core.celery_app beat --loglevel=info
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend:/app
    environment:
      - DATABASE_URL=postgresql://hustl_user:hustl_pass_2026@postgres:5432/hustl_db
      - REDIS_URL=redis://redis:6379/0
```

**✅ Результат:**
- Каждый час автоматически удаляются истёкшие временные файлы
- Освобождается место на диске
- TempUploads таблица остаётся чистой

---

**✅ Итог недели 4:**
```
✅ Backend полностью работает E2E
✅ Можно загрузить видео через API
✅ Celery обрабатывает в фоне
✅ Получаем результат через API
✅ Топ-10 ошибок сохраняется в БД

🎉 ГОТОВЫ К FRONTEND
```

---

# 📅 НЕДЕЛЯ 5-6: FRONTEND UPLOAD И PROCESSING (10 дней)

## Цель
Реализовать UI для загрузки видео и отображения прогресса обработки.

---

## День 11-13: Upload Page

**UploadPage.tsx** - drag & drop, валидация, прогресс загрузки

**✅ Итог дня 11-13:**
- ✅ Drag & drop работает
- ✅ Валидация файла
- ✅ Прогресс-бар загрузки
- ✅ Интеграция с API

---

## День 14-15: Processing Page

**ProcessingPage.tsx** - прогресс обработки, polling статуса

**✅ Итог дня 14-15:**
- ✅ Прогресс-бар обработки
- ✅ Polling статуса
- ✅ Отображение этапов
- ✅ Кнопка отмены

---

**✅ Итог недели 5-6:**
```
✅ Upload UI работает
✅ Processing UI работает
✅ Можно загрузить видео через UI
✅ Видно прогресс обработки

🎉 ГОТОВЫ К RESULTS PAGE
```

---

# 📅 НЕДЕЛЯ 7: FRONTEND RESULTS (5 дней)

## Цель
Отобразить результаты анализа: видеоплеер, скриншоты, оценки.

---

**ResultsPage.tsx, ErrorCard.tsx, VideoPlayer.tsx** - полный UI результатов

**✅ Итог недели 7:**
```
✅ ResultsPage работает
✅ Видеоплеер с ошибками
✅ Скриншоты отображаются
✅ Кнопки сохранить/отклонить

🎉 ПОЛНЫЙ E2E РАБОТАЕТ ЧЕРЕЗ UI
```

---

# 📅 НЕДЕЛЯ 8: ЛИЧНЫЙ КАБИНЕТ (5 дней)

**ProfilePage, VideoHistory, ProgressChart**

**✅ Итог недели 8:**
```
✅ Личный кабинет работает
✅ История анализов
✅ Статистика прогресса

🎉 ВСЕ ФУНКЦИИ MVP ГОТОВЫ
```

---

# 📅 НЕДЕЛЯ 9-10: ПОЛИРОВКА И ТЕСТИРОВАНИЕ (10 дней)

**UI/UX полировка, unit тесты, E2E тесты, баг-фиксинг**

**✅ Итог недели 9-10:**
```
✅ UI отполирован
✅ Тесты написаны (coverage 70%+)
✅ Все баги исправлены
✅ Система стабильна

🎉 MVP ГОТОВ К ЗАЩИТЕ
```

---

# 📅 НЕДЕЛЯ 11: ДОКУМЕНТАЦИЯ (5 дней)

**README, API docs, user guide, техническая документация для диплома**

**✅ Итог недели 11:**
```
✅ Вся документация готова
✅ README с инструкциями
✅ Документация для диплома
```

---

# 📅 НЕДЕЛЯ 12: ПРЕЗЕНТАЦИЯ (5 дней)

**PowerPoint презентация, демо-видео, репетиция защиты**

**✅ Итог недели 12:**
```
✅ Презентация готова
✅ Демо-видео записано
✅ Готов к защите
```

---

# 📅 НЕДЕЛЯ 13: РЕЗЕРВ И ЗАЩИТА

**Финальные правки, печать документов, защита диплома**

**🎓 ЗАЩИТА ДИПЛОМА**

---

# 📊 ИТОГОВАЯ СВОДКА ВСЕХ 13 НЕДЕЛЬ

| Неделя | Этап | Результат |
|--------|------|-----------|
| 1 | Подготовка | ✅ Backend + Frontend скелеты, Auth, датасет |
| 2 | Анализ ритма | ✅ Локальный анализ ритма работает |
| 3 | Claude + визуализация | ✅ Claude API, скриншоты с разметкой |
| 4 | Интеграция Celery | ✅ Backend E2E работает |
| 5-6 | Frontend Upload/Processing | ✅ Загрузка и прогресс в UI |
| 7 | Frontend Results | ✅ Отображение результатов |
| 8 | Личный кабинет | ✅ Профиль, история, статистика |
| 9-10 | Полировка и тесты | ✅ Готовый продукт |
| 11 | Документация | ✅ Вся документация |
| 12 | Презентация | ✅ Готов к защите |
| 13 | Резерв и защита | 🎓 Защита |

---

# 🎯 КРИТИЧЕСКИЙ ПУТЬ (нельзя пропустить)

```
Неделя 1 (подготовка)
  ↓
Неделя 2 (анализ ритма)
  ↓
Неделя 3 (Claude API)
  ↓
Неделя 4 (интеграция)
  ↓
Неделя 5-7 (Frontend)
  ↓
Неделя 9-10 (тестирование)
  ↓
Неделя 12 (презентация)
  ↓
ЗАЩИТА
```

**Минимум для работающего MVP: 8-9 недель**  
**Комфортно с полировкой: 12-13 недель**

---

# ✅ ФИНАЛ

**Готовый MVP включает:**
- ✅ Регистрация/вход
- ✅ Загрузка видео
- ✅ Анализ (ритм, постура, техника, музыкальность)
- ✅ Результаты со скриншотами
- ✅ Сохранение в историю
- ✅ Личный кабинет с статистикой
- ✅ Документация
- ✅ Презентация

**🎉 УСПЕШНАЯ ЗАЩИТА ДИПЛОМА!**
