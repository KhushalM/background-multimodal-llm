import time
import logging
import asyncio
import os
from typing import Optional, List
from dataclasses import dataclass
from pydantic import BaseModel
import io
import numpy as np
import soundfile as sf

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


@dataclass
class TTSConfig:
    """Configuration for OpenAI Text-to-Speech service"""

    model: str = "tts-1"  # OpenAI's high-quality TTS model
    voice: str = "alloy"  # alloy, echo, fable, onyx, nova, shimmer
    response_format: str = "wav"  # mp3, opus, aac, flac, wav, pcm
    speed: float = 1.0  # 0.25 to 4.0
    sample_rate: int = 16000  # Target sample rate for consistency
    max_retries: int = 3
    timeout: float = 30.0


class TTSRequest(BaseModel):
    """Request for text-to-speech conversion"""

    text: str
    voice_preset: str = "default"
    speed: float = 1.0
    pitch: float = 1.0  # Not used in OpenAI TTS, kept for compatibility
    session_id: Optional[str] = None


class TTSResponse(BaseModel):
    """Response from text-to-speech conversion"""

    audio_data: List[float]  # Audio samples as float list
    sample_rate: int
    duration: float
    processing_time: float
    text: str
    audio_format: str = "wav"


class TTSService:
    """Text-to-Speech service using OpenAI TTS API"""

    def __init__(self, config: TTSConfig, api_key: str = None):
        self.config = config

        # Load API key from parameter or environment (same as STT service)
        actual_api_key = api_key or os.getenv("OPENAI_KEY")
        if not actual_api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_KEY environment " "variable or pass api_key parameter.")

        self.client = AsyncOpenAI(api_key=actual_api_key)
        self._voice_mapping = {"default": "alloy", "male": "onyx", "female": "nova", "neutral": "echo", "friendly": "alloy", "professional": "fable", "warm": "shimmer"}

        logger.info(f"OpenAI TTS service initialized with model: {self.config.model}")

    async def __aenter__(self):
        """Initialize the service asynchronously"""
        try:
            # Test the service with a simple request
            logger.info("Testing OpenAI TTS service...")
            test_result = await self._test_service()
            if test_result:
                logger.info("OpenAI TTS service ready")
            else:
                logger.warning("OpenAI TTS service test failed")

        except Exception as e:
            logger.error(f"Error initializing OpenAI TTS service: {e}")
            raise

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup resources"""
        if hasattr(self.client, "close"):
            await self.client.close()

    def _get_openai_voice(self, voice_preset: str) -> str:
        """Map voice preset to OpenAI voice"""
        return self._voice_mapping.get(voice_preset, "alloy")

    def _preprocess_text(self, text: str) -> str:
        """Clean and prepare text for TTS"""
        # Remove or replace problematic characters
        text = text.strip()

        # Handle common replacements for better pronunciation
        replacements = {
            "&": "and",
            "@": "at",
            "#": "hashtag",
            "$": "dollar",
            "%": "percent",
            "...": "...",  # Keep ellipsis as is for OpenAI
            "—": " - ",
            "–": " - ",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        # OpenAI TTS has a 4096 character limit
        max_chars = 4000  # Leave some buffer

        if len(text) > max_chars:
            # Try to split at sentence boundaries
            sentences = text.replace(". ", ".\n").split("\n")

            # Build text up to character limit
            result_text = ""
            for sentence in sentences:
                test_text = result_text + sentence + ". "
                if len(test_text) > max_chars:
                    break
                result_text = test_text

            # If we got at least one sentence, use it
            if result_text.strip():
                text = result_text.strip()
            else:
                # Fallback: truncate at word boundary
                text = text[:max_chars].rsplit(" ", 1)[0] + "."

        return text

    async def _convert_audio_to_samples(self, audio_bytes: bytes) -> np.ndarray:
        """Convert audio bytes to numpy array samples"""
        try:
            # Use soundfile to read the audio data
            with io.BytesIO(audio_bytes) as audio_buffer:
                audio_data, original_sample_rate = sf.read(audio_buffer)

                # Convert to mono if stereo
                if len(audio_data.shape) > 1:
                    audio_data = np.mean(audio_data, axis=1)

                # Resample to target sample rate if needed
                if original_sample_rate != self.config.sample_rate:
                    # Simple resampling using linear interpolation
                    ratio = self.config.sample_rate / original_sample_rate
                    new_length = int(len(audio_data) * ratio)
                    audio_data = np.interp(np.linspace(0, len(audio_data) - 1, new_length), np.arange(len(audio_data)), audio_data)

                return audio_data

        except Exception as e:
            logger.error(f"Error converting audio: {e}")
            # Return 1 second of silence as fallback
            return np.zeros(self.config.sample_rate)

    async def synthesize_speech(self, request: TTSRequest) -> TTSResponse:
        """Convert text to speech using OpenAI TTS"""
        start_time = time.time()

        try:
            # Preprocess text
            processed_text = self._preprocess_text(request.text)

            # Get OpenAI voice
            voice = self._get_openai_voice(request.voice_preset)

            # Adjust speed
            speed = max(0.25, min(4.0, request.speed))

            logger.info(f"Synthesizing speech with OpenAI: {processed_text[:100]}... " f"(voice: {voice}, speed: {speed})")

            # Call OpenAI TTS API
            response = await self.client.audio.speech.create(model=self.config.model, voice=voice, input=processed_text, response_format=self.config.response_format, speed=speed)

            # Get audio bytes
            audio_bytes = await response.aread()

            # Convert to numpy array
            audio_data = await self._convert_audio_to_samples(audio_bytes)

            # Calculate metrics
            duration = len(audio_data) / self.config.sample_rate
            processing_time = time.time() - start_time

            logger.info(f"Generated {duration:.2f}s of audio in {processing_time:.2f}s")

            return TTSResponse(audio_data=audio_data.tolist(), sample_rate=self.config.sample_rate, duration=duration, processing_time=processing_time, text=processed_text, audio_format="wav")

        except Exception as e:
            logger.error(f"Error in OpenAI TTS synthesize_speech: {e}")

            # Return silence on failure
            duration = 1.0  # 1 second of silence
            silence = np.zeros(int(duration * self.config.sample_rate))

            return TTSResponse(
                audio_data=silence.tolist(),
                sample_rate=self.config.sample_rate,
                duration=duration,
                processing_time=time.time() - start_time,
                text=request.text,
                audio_format="silence",
            )

    async def synthesize_batch(self, texts: List[str], session_id: Optional[str] = None) -> List[TTSResponse]:
        """Synthesize multiple texts in batch"""
        responses = []

        for text in texts:
            request = TTSRequest(text=text, session_id=session_id)
            response = await self.synthesize_speech(request)
            responses.append(response)

            # Small delay between requests to respect rate limits
            await asyncio.sleep(0.1)

        return responses

    def get_supported_voices(self) -> List[str]:
        """Get list of supported voice presets"""
        return list(self._voice_mapping.keys())

    async def _test_service(self) -> bool:
        """Test if the TTS service is working"""
        try:
            test_request = TTSRequest(text="Test.", voice_preset="default")
            response = await self.synthesize_speech(test_request)
            return len(response.audio_data) > 0 and response.audio_format != "silence"

        except Exception as e:
            logger.error(f"OpenAI TTS test failed: {e}")
            return False

    async def test_synthesis(self) -> bool:
        """Test if the TTS service is working (public method for compatibility)"""
        return await self._test_service()


# Factory function for easy instantiation
async def create_tts_service(model_name: str = "tts-1", api_key: Optional[str] = None, **config_kwargs) -> TTSService:
    """Create and initialize OpenAI TTS service"""

    # Map model name for compatibility
    if model_name == "microsoft/speecht5_tts":
        model_name = "tts-1"  # Default mapping
    elif model_name not in ["gpt-4o-mini-tts", "tts-1", "tts-1-hd"]:
        logger.warning(f"Unknown model {model_name}, using gpt-4o-mini-tts")
        model_name = "tts-1"

    config = TTSConfig(model=model_name, **config_kwargs)
    service = TTSService(config, api_key)  # api_key can be None now

    # Service will be tested when entering async context (in __aenter__)
    logger.info("OpenAI TTS service created")
    return service
