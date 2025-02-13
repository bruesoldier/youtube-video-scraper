import yt_dlp
import os
from typing import Dict, Optional
import whisper
from sqlalchemy.orm import Session
from ..models import Video, Transcription
import re

class VideoService:
    def __init__(self):
        self.model = whisper.load_model("base")
        self.download_path = "downloads"
        os.makedirs(self.download_path, exist_ok=True)
    
    def extract_video_id(self, url: str) -> Optional[str]:
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)',
            r'(?:youtube\.com\/embed\/)([\w-]+)',
            r'(?:youtube\.com\/v\/)([\w-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def get_video_info(self, url: str) -> Dict:
        ydl_opts = {
            'format': 'bestaudio/best',
            'extract_audio': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info['title'],
                'description': info.get('description', ''),
                'youtube_id': info['id'],
            }
    
    def download_audio(self, youtube_id: str) -> str:
        output_path = os.path.join(self.download_path, f"{youtube_id}.mp3")
        
        if os.path.exists(output_path):
            return output_path
            
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(self.download_path, f"{youtube_id}.%(ext)s"),
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={youtube_id}"])
        
        return output_path
    
    def transcribe_audio(self, audio_path: str) -> str:
        result = self.model.transcribe(audio_path)
        return result["text"]
    
    def process_video(self, db: Session, url: str, user_id: int, category: str) -> Video:
        video_info = self.get_video_info(url)
        
        video = Video(
            youtube_id=video_info['youtube_id'],
            title=video_info['title'],
            description=video_info['description'],
            category=category,
            user_id=user_id
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        
        audio_path = self.download_audio(video_info['youtube_id'])
        transcription_text = self.transcribe_audio(audio_path)
        
        transcription = Transcription(
            video_id=video.id,
            content=transcription_text
        )
        db.add(transcription)
        db.commit()
        
        try:
            os.remove(audio_path)
        except:
            pass
        
        return video
