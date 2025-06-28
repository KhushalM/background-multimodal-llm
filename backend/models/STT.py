from pydantic import BaseModel
import asyncio
import logging
import numpy as np
import time
import io
import os
from typing import Optional, List, AsyncGenerator
from dataclasses import dataclass
import openai
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


@dataclass
class STTConfig:
    """Configuration for Speech-to-Text service"""

    model_name: str = "whisper-1"  # OpenAI Whisper model
    api_key: Optional[str] = None  # Will use OPENAI_API_KEY env var if not provided
    sample_rate: int = 16000
    min_speech_duration: float = 0.5  # Minimum speech duration to process (seconds)
    max_speech_duration: float = 30.0  # Maximum speech duration to prevent memory issues
    max_retries: int = 3
    language: Optional[str] = None  # Auto-detect if None
    temperature: float = 0.0  # For consistent transcriptions
    response_format: str = "json"  # json, text, srt, verbose_json, or vtt


class AudioChunk(BaseModel):
    """Pydantic model for audio data"""

    data: List[float]
    sample_rate: int = 16000
    timestamp: float
    chunk_id: Optional[str] = None


class TranscriptionResult(BaseModel):
    """Pydantic model for transcription results"""

    text: str
    confidence: Optional[float] = None
    timestamp: float
    chunk_id: Optional[str] = None
    processing_time: Optional[float] = None


class SpeechSession:
    """Represents a continuous speech session"""

    def __init__(self, session_id: str, start_timestamp: float):
        self.session_id = session_id
        self.start_timestamp = start_timestamp
        self.audio_buffer: List[float] = []
        self.sample_rate = 16000
        self.is_active = True
        self.last_audio_timestamp = start_timestamp

    def add_audio(self, audio_data: List[float], timestamp: float):
        """Add audio data to this speech session"""
        self.audio_buffer.extend(audio_data)
        self.last_audio_timestamp = timestamp

    def get_duration(self) -> float:
        """Get the duration of accumulated audio in seconds"""
        return len(self.audio_buffer) / self.sample_rate

    def to_audio_chunk(self) -> AudioChunk:
        """Convert the accumulated audio to an AudioChunk"""
        return AudioChunk(
            data=self.audio_buffer.copy(),
            sample_rate=self.sample_rate,
            timestamp=self.start_timestamp,
            chunk_id=f"speech_session_{self.session_id}",
        )


class STTService:
    """Speech-to-Text service using OpenAI Whisper API"""

    def __init__(self, config: STTConfig):
        self.config = config

        # Initialize OpenAI client
        api_key = config.api_key or os.getenv("OPENAI_KEY")
        if not api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_KEY environment " "variable or pass api_key in config.")

        self.client = openai.OpenAI(api_key=api_key)

        # Create dedicated ThreadPoolExecutor to avoid semaphore leaks
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="stt", initializer=None, initargs=())

        # Speech session management
        self.current_session: Optional[SpeechSession] = None
        self.session_counter = 0

        logger.info(f"STT service initialized with OpenAI Whisper model: " f"{self.config.model_name}")

    async def __aenter__(self):
        """Initialize the service asynchronously"""
        try:
            # Test API connection with a minimal request
            logger.info("Testing OpenAI API connection...")
            # We'll test the connection when we make the first actual request
            logger.info("STT service ready")
        except Exception as e:
            logger.error(f"Error initializing STT service: {e}")
            raise

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup resources"""
        # Shutdown the executor to prevent semaphore leaks
        if hasattr(self, "executor") and self.executor:
            try:
                self.executor.shutdown(wait=False)
                self.executor.shutdown(wait=True)
            except Exception as e:
                logger.warning(f"Error shutting down STT executor: {e}")
            finally:
                self.executor = None

    def _preprocess_audio(self, audio_data: List[float], sample_rate: int) -> np.ndarray:
        """Convert audio data to the format expected by OpenAI Whisper"""
        try:
            # Convert to numpy array
            audio_array = np.array(audio_data, dtype=np.float32)

            # Resample if necessary (Whisper can handle various sample rates,
            # but 16kHz is optimal)
            if sample_rate != self.config.sample_rate:
                # Simple resampling (for production, use librosa)
                ratio = self.config.sample_rate / sample_rate
                new_length = int(len(audio_array) * ratio)
                audio_array = np.interp(
                    np.linspace(0, len(audio_array) - 1, new_length),
                    np.arange(len(audio_array)),
                    audio_array,
                )

            # Normalize audio
            if np.max(np.abs(audio_array)) > 0:
                audio_array = audio_array / np.max(np.abs(audio_array))

            return audio_array

        except Exception as e:
            logger.error(f"Error preprocessing audio: {e}")
            raise

    def _audio_to_wav_bytes(self, audio_array: np.ndarray, sample_rate: int) -> bytes:
        """Convert numpy audio array to WAV bytes for OpenAI API"""
        try:
            import wave

            # Create WAV file in memory
            wav_buffer = io.BytesIO()

            with wave.open(wav_buffer, "wb") as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)

                # Convert float32 to int16
                audio_int16 = (audio_array * 32767).astype(np.int16)
                wav_file.writeframes(audio_int16.tobytes())

            wav_buffer.seek(0)
            return wav_buffer.getvalue()

        except Exception as e:
            logger.error(f"Error converting audio to WAV: {e}")
            raise

    async def _transcribe_with_openai(self, audio_array: np.ndarray, sample_rate: int) -> str:
        """Transcribe audio using OpenAI Whisper API"""
        try:
            # Convert audio to WAV format
            wav_bytes = self._audio_to_wav_bytes(audio_array, sample_rate)

            # Create a file-like object for the API
            audio_file = io.BytesIO(wav_bytes)
            audio_file.name = "audio.wav"  # OpenAI API requires a filename

            # Make API call
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.client.audio.transcriptions.create(
                    model=self.config.model_name, file=audio_file, language=self.config.language, temperature=self.config.temperature, response_format=self.config.response_format
                ),
            )

            # Extract text based on response format
            if self.config.response_format == "json":
                return response.text
            elif self.config.response_format == "verbose_json":
                return response.text
            else:
                return str(response)

        except Exception as e:
            logger.error(f"Error transcribing with OpenAI: {e}")
            raise

    async def transcribe_chunk(self, audio_chunk: AudioChunk) -> TranscriptionResult:
        """Transcribe an audio chunk using OpenAI Whisper API"""
        if not audio_chunk or not audio_chunk.data:
            return TranscriptionResult(
                text="",
                timestamp=audio_chunk.timestamp if audio_chunk else time.time(),
                chunk_id=audio_chunk.chunk_id if audio_chunk else None,
                processing_time=0.0,
            )

        start_time = time.time()

        try:
            # Check duration
            duration = len(audio_chunk.data) / audio_chunk.sample_rate
            if duration < self.config.min_speech_duration:
                logger.debug(f"Audio chunk too short: {duration:.2f}s < " f"{self.config.min_speech_duration}s")
                return TranscriptionResult(
                    text="",
                    timestamp=audio_chunk.timestamp,
                    chunk_id=audio_chunk.chunk_id,
                    processing_time=time.time() - start_time,
                )

            if duration > self.config.max_speech_duration:
                logger.warning(f"Audio chunk too long: {duration:.2f}s > " f"{self.config.max_speech_duration}s, truncating")
                max_samples = int(self.config.max_speech_duration * audio_chunk.sample_rate)
                audio_chunk.data = audio_chunk.data[:max_samples]

            # Preprocess audio
            audio_array = self._preprocess_audio(audio_chunk.data, audio_chunk.sample_rate)

            # Transcribe with retries
            text = ""
            last_error = None

            for attempt in range(self.config.max_retries):
                try:
                    text = await self._transcribe_with_openai(audio_array, audio_chunk.sample_rate)
                    break
                except Exception as e:
                    last_error = e
                    if attempt < self.config.max_retries - 1:
                        wait_time = 2**attempt  # Exponential backoff
                        logger.warning(f"Transcription attempt {attempt + 1} failed, " f"retrying in {wait_time}s: {e}")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"All transcription attempts failed: {e}")
                        raise e

            processing_time = time.time() - start_time

            result = TranscriptionResult(
                text=text.strip(),
                timestamp=audio_chunk.timestamp,
                chunk_id=audio_chunk.chunk_id,
                processing_time=processing_time,
            )

            logger.debug(f"Transcribed in {processing_time:.2f}s: " f"'{result.text[:50]}{'...' if len(result.text) > 50 else ''}'")
            return result

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Error transcribing audio chunk: {e}")
            return TranscriptionResult(
                text="",
                timestamp=audio_chunk.timestamp,
                chunk_id=audio_chunk.chunk_id,
                processing_time=processing_time,
            )

    def process_audio_with_vad(
        self,
        audio_data: List[float],
        sample_rate: int,
        vad_info: dict,
        timestamp: float,
    ) -> Optional[AudioChunk]:
        """
        Process audio data with VAD information to manage speech sessions.

        Args:
            audio_data: Raw audio samples
            sample_rate: Audio sample rate
            vad_info: VAD information containing speech detection results
            timestamp: Timestamp of the audio data

        Returns:
            AudioChunk if speech session is complete, None if still accumulating
        """
        try:
            is_speech = vad_info.get("isSpeaking", False)  # Use frontend's key
            speech_probability = vad_info.get("confidence", 0.0)  # Use frontend's key

            # If this is speech and we don't have an active session, start one
            if is_speech and self.current_session is None:
                self.session_counter += 1
                session_id = f"{int(timestamp)}_{self.session_counter}"
                self.current_session = SpeechSession(session_id, timestamp)
                logger.info(f"Started new speech session: {session_id}")

            # If we have an active session, add audio to it
            if self.current_session is not None:
                self.current_session.add_audio(audio_data, timestamp)

                # Check if we should complete the session
                session_duration = self.current_session.get_duration()

                # Complete session if:
                # 1. No longer detecting speech (end of speech)
                # 2. Session has reached maximum duration
                # 3. There's a significant gap in audio timestamps
                time_gap = timestamp - self.current_session.last_audio_timestamp
                should_complete = (
                    not is_speech or session_duration >= self.config.max_speech_duration or time_gap > 2.0  # End of speech detected  # Max duration reached  # Significant time gap (> 2 seconds)
                )

                if should_complete:
                    return self._complete_current_session()

            return None

        except Exception as e:
            logger.error(f"Error processing audio with VAD: {e}")
            # If there's an error, try to complete the current session
            if self.current_session is not None:
                return self._complete_current_session()
            return None

    def _complete_current_session(self) -> Optional[AudioChunk]:
        """Complete the current speech session and return the accumulated audio"""
        if self.current_session is None:
            return None

        try:
            # Check if we have enough audio to process
            duration = self.current_session.get_duration()
            if duration < self.config.min_speech_duration:
                logger.debug(f"Speech session too short: {duration:.2f}s, discarding")
                self.current_session = None
                return None

            # Convert to audio chunk
            audio_chunk = self.current_session.to_audio_chunk()
            session_id = self.current_session.session_id

            # Clear the current session
            self.current_session = None

            logger.info(f"Completed speech session {session_id}: {duration:.2f}s")
            return audio_chunk

        except Exception as e:
            logger.error(f"Error completing speech session: {e}")
            self.current_session = None
            return None

    def add_audio_to_buffer(self, audio_data: List[float], sample_rate: int) -> Optional[AudioChunk]:
        """Legacy method for backward compatibility - creates a simple audio chunk"""
        timestamp = time.time()
        return AudioChunk(data=audio_data, sample_rate=sample_rate, timestamp=timestamp)

    async def transcribe_streaming(self, audio_stream) -> AsyncGenerator[TranscriptionResult, None]:
        """Transcribe streaming audio (placeholder for future implementation)"""
        # This would require implementing streaming with OpenAI API
        # For now, we'll process chunks as they come
        async for audio_chunk in audio_stream:
            result = await self.transcribe_chunk(audio_chunk)
            if result.text:
                yield result

    def flush_buffer(self) -> Optional[AudioChunk]:
        """Flush any remaining audio in the buffer"""
        if self.current_session is not None:
            return self._complete_current_session()
        return None


async def create_stt_service(model_name: str = "whisper-1", **config_kwargs) -> STTService:
    """Create and initialize STT service"""
    config = STTConfig(model_name=model_name, **config_kwargs)
    return STTService(config)
