from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from pydantic import BaseModel

from .database import get_db, engine
from . import models
from .services.video_service import VideoService
from .services.ai_service import AIService
import os
from dotenv import load_dotenv

load_dotenv()
models.Base.metadata.create_all(bind=engine)

app = FastAPI()
video_service = VideoService()
ai_service = AIService()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    email: str
    username: str
    password: str

class VideoCreate(BaseModel):
    url: str
    category: Optional[str] = None

class MessageCreate(BaseModel):
    content: str
    video_id: int
    parent_id: Optional[int] = None

@app.post("/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    access_token = create_access_token(data={"sub": db_user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@app.post("/videos")
def create_video(video: VideoCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    try:
        video_info = video_service.get_video_info(video.url)
        if not video.category:
            video.category = ai_service.suggest_category(video_info['title'], video_info['description'])
        db_video = video_service.process_video(db=db, url=video.url, user_id=current_user.id, category=video.category)
        return {"message": "Video processed successfully", "video_id": db_video.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/videos")
def get_videos(category: Optional[str] = None, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    query = db.query(models.Video)
    if category:
        query = query.filter(models.Video.category == category)
    return query.all()

@app.get("/videos/{video_id}")
def get_video(video_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video

@app.post("/messages")
def create_message(message: MessageCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_message = models.Message(
        content=message.content,
        user_id=current_user.id,
        video_id=message.video_id,
        parent_id=message.parent_id
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    ai_response = ai_service.generate_response(db, message.video_id, message.content)
    ai_message = models.Message(
        content=ai_response,
        video_id=message.video_id,
        parent_id=db_message.id
    )
    db.add(ai_message)
    db.commit()
    
    return {"user_message": db_message, "ai_response": ai_message}

@app.get("/messages/{video_id}")
def get_messages(video_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    messages = db.query(models.Message).filter(models.Message.video_id == video_id).order_by(models.Message.created_at).all()
    return messages
