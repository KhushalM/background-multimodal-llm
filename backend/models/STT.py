from pydantic import BaseModel
import asyncio
import logging
import numpy as np
import time
from typing import Optional, List, AsyncGenerator
from dataclasses import dataclass
import torch
from transformers import pipeline, AutoProcessor, AutoModelForSpeechSeq2Seq

logger = logging.getLogger(__name__)


@dataclass
class STTConfig:
    """Configuration for Speech-to-Text service"""

    model_name: str = "distil-whisper/distil-large-v3.5"
    device: str = "auto"  # "auto", "cpu", or "cuda"
    torch_dtype: str = "auto"  # "auto", "float16", "float32"
    sample_rate: int = 16000
    min_speech_duration: float = 0.5  # Minimum speech duration to process (seconds)
    max_speech_duration: float = (
        30.0  # Maximum speech duration to prevent memory issues
    )
    max_retries: int = 3
    use_flash_attention_2: bool = False  # Set to True if supported


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
    """Speech-to-Text service using HuggingFace Transformers pipeline"""

    def __init__(self, config: STTConfig):
        self.config = config
        self.pipeline = None
        self.device = self._get_device()
        self.torch_dtype = self._get_torch_dtype()

        # Speech session management
        self.current_session: Optional[SpeechSession] = None
        self.session_counter = 0

        logger.info(
            f"STT service initialized with device: {self.device}, dtype: {self.torch_dtype}"
        )

    def _get_device(self) -> str:
        """Determine the best device to use"""
        if self.config.device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"  # Apple Silicon GPU
            else:
                return "cpu"
        return self.config.device

    def _get_torch_dtype(self):
        """Determine the best torch dtype to use"""
        if self.config.torch_dtype == "auto":
            if self.device == "cuda":
                return torch.float16
            else:
                return torch.float32
        elif self.config.torch_dtype == "float16":
            return torch.float16
        else:
            return torch.float32

    async def __aenter__(self):
        """Initialize the pipeline asynchronously"""
        try:
            logger.info(f"Loading STT model: {self.config.model_name}")

            # Load model and processor
            model = AutoModelForSpeechSeq2Seq.from_pretrained(
                self.config.model_name,
                torch_dtype=self.torch_dtype,
                low_cpu_mem_usage=True,
                use_safetensors=True,
                attn_implementation=(
                    "flash_attention_2" if self.config.use_flash_attention_2 else None
                ),
            )
            model.to(self.device)

            processor = AutoProcessor.from_pretrained(self.config.model_name)

            # Create pipeline
            self.pipeline = pipeline(
                "automatic-speech-recognition",
                model=model,
                tokenizer=processor.tokenizer,
                feature_extractor=processor.feature_extractor,
                max_new_tokens=128,
                chunk_length_s=30,
                batch_size=16,
                return_timestamps=True,
                torch_dtype=self.torch_dtype,
                device=self.device,
            )

            logger.info("STT pipeline loaded successfully")

        except Exception as e:
            logger.error(f"Error loading STT pipeline: {e}")
            raise

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup resources"""
        if self.pipeline is not None:
            # Clear CUDA cache if using GPU
            if self.device == "cuda":
                torch.cuda.empty_cache()
            self.pipeline = None

    def _preprocess_audio(
        self, audio_data: List[float], sample_rate: int
    ) -> np.ndarray:
        """Convert audio data to the format expected by Whisper"""
        try:
            # Convert to numpy array
            audio_array = np.array(audio_data, dtype=np.float32)

            # Resample if necessary (Whisper expects 16kHz)
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

    async def transcribe_chunk(self, audio_chunk: AudioChunk) -> TranscriptionResult:
        """Transcribe a single audio chunk"""
        start_time = time.time()

        try:
            if self.pipeline is None:
                raise RuntimeError(
                    "STT pipeline not initialized. Use 'async with' context manager."
                )

            # Preprocess audio
            audio_array = self._preprocess_audio(
                audio_chunk.data, audio_chunk.sample_rate
            )

            # Run inference with pipeline
            # Run in executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.pipeline(
                    audio_array,
                    generate_kwargs={"language": "english"},
                    return_timestamps=True,
                ),
            )

            # Extract text from result
            text = ""
            if isinstance(result, dict):
                text = result.get("text", "").strip()
            elif isinstance(result, list) and len(result) > 0:
                text = result[0].get("text", "").strip()

            processing_time = time.time() - start_time

            logger.info(
                f"Transcribed speech session: '{text}' in {processing_time:.2f}s"
            )

            return TranscriptionResult(
                text=text,
                timestamp=audio_chunk.timestamp,
                chunk_id=audio_chunk.chunk_id,
                processing_time=processing_time,
            )

        except Exception as e:
            logger.error(f"Error in transcribe_chunk: {e}")

            # Return empty result on failure
            return TranscriptionResult(
                text="",
                timestamp=audio_chunk.timestamp,
                chunk_id=audio_chunk.chunk_id,
                processing_time=time.time() - start_time,
            )

    def process_audio_with_vad(
        self,
        audio_data: List[float],
        sample_rate: int,
        vad_info: dict,
        timestamp: float,
    ) -> Optional[AudioChunk]:
        """
        Process audio data with VAD information to manage speech sessions

        Args:
            audio_data: Raw audio samples
            sample_rate: Audio sample rate
            vad_info: VAD information containing isSpeaking, energy, confidence
            timestamp: Timestamp of the audio data

        Returns:
            AudioChunk if a complete speech session is ready for transcription, None otherwise
        """
        is_speaking = vad_info.get("isSpeaking", False)

        if is_speaking:
            # Speech is active
            if self.current_session is None:
                # Start new speech session
                self.session_counter += 1
                session_id = f"session_{self.session_counter}_{int(timestamp)}"
                self.current_session = SpeechSession(session_id, timestamp)
                logger.debug(f"Started new speech session: {session_id}")

            # Add audio to current session
            self.current_session.add_audio(audio_data, timestamp)

            # Check if session is getting too long (prevent memory issues)
            if self.current_session.get_duration() > self.config.max_speech_duration:
                logger.warning(
                    f"Speech session exceeded max duration ({self.config.max_speech_duration}s), forcing completion"
                )
                return self._complete_current_session()

        else:
            # Speech has ended
            if self.current_session is not None:
                # Complete the current session
                return self._complete_current_session()

        return None

    def _complete_current_session(self) -> Optional[AudioChunk]:
        """Complete the current speech session and return it as an AudioChunk"""
        if self.current_session is None:
            return None

        session_duration = self.current_session.get_duration()

        # Only process if we have enough audio
        if session_duration >= self.config.min_speech_duration:
            logger.info(
                f"Completing speech session {self.current_session.session_id} with {session_duration:.2f}s of audio"
            )
            audio_chunk = self.current_session.to_audio_chunk()
            self.current_session = None
            return audio_chunk
        else:
            logger.debug(
                f"Speech session too short ({session_duration:.2f}s), discarding"
            )
            self.current_session = None
            return None

    # Legacy methods for backward compatibility
    def add_audio_to_buffer(
        self, audio_data: List[float], sample_rate: int
    ) -> Optional[AudioChunk]:
        """
        Legacy method for backward compatibility
        This method is deprecated - use process_audio_with_vad instead
        """
        logger.warning(
            "add_audio_to_buffer is deprecated, use process_audio_with_vad instead"
        )

        # For backward compatibility, assume speech is always active
        vad_info = {"isSpeaking": True}
        return self.process_audio_with_vad(
            audio_data, sample_rate, vad_info, time.time()
        )

    async def transcribe_streaming(
        self, audio_stream
    ) -> AsyncGenerator[TranscriptionResult, None]:
        """Transcribe streaming audio data"""
        async for audio_data, sample_rate in audio_stream:
            # For streaming, assume speech is always active
            vad_info = {"isSpeaking": True}
            chunk = self.process_audio_with_vad(
                audio_data, sample_rate, vad_info, time.time()
            )
            if chunk:
                result = await self.transcribe_chunk(chunk)
                if result.text:  # Only yield non-empty results
                    yield result

    def flush_buffer(self) -> Optional[AudioChunk]:
        """Flush any remaining speech session"""
        return self._complete_current_session()


# Factory function for easy instantiation
async def create_stt_service(
    model_name: str = "distil-whisper/distil-large-v3.5", **config_kwargs
) -> STTService:
    """Create and initialize STT service"""
    config = STTConfig(model_name=model_name, **config_kwargs)
    return STTService(config)
