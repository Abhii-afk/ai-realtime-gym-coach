from io import BytesIO
from gtts import gTTS
import logging
import hashlib

logger = logging.getLogger(__name__)


class TextToSpeech:
    def __init__(self):
        self._cache = {}

    def speak(self, text, lang="en"):
        cleaned = (text or "").strip()

        if not cleaned:
            logger.warning("TTS: Empty text provided, returning None")
            return None

        logger.info(f"TTS: Generating audio for text: {repr(cleaned[:100])}")

        cache_key = hashlib.md5(f"{cleaned}:{lang}".encode()).hexdigest()
        if cache_key in self._cache:
            logger.info(f"TTS: Cache hit for key {cache_key[:8]}")
            return self._cache[cache_key]

        try:
            buffer = BytesIO()
            gTTS(text=cleaned, lang=lang).write_to_fp(buffer)
            buffer.seek(0)
            audio_data = buffer.read()
            
            if not audio_data:
                logger.error("TTS: Generated empty audio data")
                return None
                
            logger.info(f"TTS: Generated {len(audio_data)} bytes of audio (MP3)")
            self._cache[cache_key] = audio_data
            return audio_data
        except Exception as e:
            logger.error(f"TTS generation error: {e}", exc_info=True)
            return None
        