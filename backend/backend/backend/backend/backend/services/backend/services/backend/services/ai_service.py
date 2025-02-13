import os
from typing import List
import openai
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from ..models import Message, Video, Transcription

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

class AIService:
    def __init__(self):
        self.model = "gpt-3.5-turbo"
        self.max_context_length = 4000
    
    def _prepare_context(self, db: Session, video_id: int) -> str:
        video = db.query(Video).filter(Video.id == video_id).first()
        transcription = db.query(Transcription).filter(Transcription.video_id == video_id).first()
        
        recent_messages = (
            db.query(Message)
            .filter(Message.video_id == video_id)
            .order_by(Message.created_at.desc())
            .limit(5)
            .all()
        )
        
        context = f"Video Title: {video.title}\n"
        context += f"Video Description: {video.description}\n"
        context += f"Category: {video.category}\n\n"
        
        if transcription:
            context += f"Transcription excerpt: {transcription.content[:500]}...\n\n"
        
        if recent_messages:
            context += "Recent discussion:\n"
            for msg in reversed(recent_messages):
                context += f"User: {msg.content}\n"
        
        return context[:self.max_context_length]
    
    def generate_response(self, db: Session, video_id: int, user_message: str) -> str:
        context = self._prepare_context(db, video_id)
        
        messages = [
            {"role": "system", "content": "You are a helpful AI assistant discussing YouTube video content. "
             "Provide insightful analysis and engage in meaningful discussion about the video's content, "
             "while maintaining a friendly and informative tone."},
            {"role": "user", "content": f"Context:\n{context}\n\nUser message: {user_message}"}
        ]
        
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                max_tokens=500,
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"I apologize, but I encountered an error while processing your request. Please try again later. Error: {str(e)}"
    
    def suggest_category(self, title: str, description: str) -> str:
        prompt = f"""Based on the following YouTube video information, suggest an appropriate category:
Title: {title}
Description: {description}

Please respond with just the category name from these options:
- Tech News
- AI News
- Tutorial
- Entertainment
- Education
- Gaming
- Music
- Other"""
        
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a content categorization assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except:
            return "Other"
