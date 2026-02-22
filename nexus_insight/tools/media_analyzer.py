import os
import logging
import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, List
import yt_dlp
from faster_whisper import WhisperModel
import redis
from nexus_insight.cognition.state import RawSource, SourceType
from nexus_insight.config import settings

logger = logging.getLogger(__name__)

class MediaAnalyzer:
    """
    Video/Audio analyzer using yt-dlp for download and faster-whisper for local transcription.
    Caches results in Redis.
    """

    def __init__(self):
        self.redis_client = None
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception as e:
            logger.warning(f"Redis not available for media cache: {e}")
        
        self._whisper_model = None

    def _get_whisper_model(self) -> WhisperModel:
        if self._whisper_model is None:
            logger.info(f"Loading Whisper model: {settings.WHISPER_MODEL}")
            self._whisper_model = WhisperModel(
                settings.WHISPER_MODEL, 
                device="auto", 
                compute_type="auto"
            )
        return self._whisper_model

    async def process_video(self, url: str) -> RawSource:
        """Main entry point for video processing"""
        cache_key = f"transcript:{hashlib.sha256(url.encode()).hexdigest()}"
        
        # Check cache
        if self.redis_client:
            cached = self.redis_client.get(cache_key)
            if cached:
                logger.info("Found transcript in cache")
                data = json.loads(cached)
                return RawSource(**data)

        # Download and transcribe
        try:
            audio_path, metadata = self._download_audio(url)
            transcript = self._transcribe(audio_path)
            
            # Clean up audio file
            if os.path.exists(audio_path):
                os.remove(audio_path)

            source = RawSource(
                id=f"media-{hash(url)}",
                source_type=SourceType.VIDEO,
                url=url,
                content=transcript,
                metadata=metadata,
                trust_score=0.70,
                fetched_at=datetime.now()
            )

            # Store in cache
            if self.redis_client:
                self.redis_client.setex(cache_key, 86400, source.model_dump_json())

            return source

        except Exception as e:
            logger.error(f"Failed to process video {url}: {e}")
            return RawSource(
                id=f"media-error-{hash(url)}",
                source_type=SourceType.VIDEO,
                url=url,
                content="",
                metadata={"error": str(e)},
                trust_score=0.0,
                fetched_at=datetime.now()
            )

    def _download_audio(self, url: str) -> tuple[str, Dict]:
        temp_dir = "/tmp/nexus_media"
        os.makedirs(temp_dir, exist_ok=True)
        
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "outtmpl": f"{temp_dir}/%(id)s.%(ext)s",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            audio_path = f"{temp_dir}/{info['id']}.mp3"
            metadata = {
                "title": info.get("title"),
                "uploader": info.get("uploader"),
                "duration": info.get("duration"),
                "upload_date": info.get("upload_date"),
                "description": info.get("description", "")[:500]
            }
            return audio_path, metadata

    def _transcribe(self, audio_path: str) -> str:
        model = self._get_whisper_model()
        segments, info = model.transcribe(audio_path, beam_size=5)
        
        full_transcript = []
        for segment in segments:
            m, s = divmod(int(segment.start), 60)
            h, m = divmod(m, 60)
            timestamp = f"[{h:02d}:{m:02d}:{s:02d}]"
            full_transcript.append(f"{timestamp} {segment.text}")
            
        return "\n".join(full_transcript)
