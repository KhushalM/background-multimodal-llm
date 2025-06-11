from pydantic import BaseModel
import asyncio
import io
import logging
import numpy as np
import time
from typing import Optional, Union, List, AsyncGenerator
import httpx
import json
import base64
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class STTConfig:
    """Configuration for Speech-to-Text service"""

    model_name: str = "distil-whisper/distil-large-v3.5"
    hf_token: Optional[str] = None
    sample_rate: int = 16000
    chunk_duration: float = 2.0  # seconds
    max_retries: int = 3
    timeout: float = 30.0


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


class STTService:
    """Speech-to-Text service using HuggingFace Inference API"""

    def __init__(self, config: STTConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=config.timeout)
        self.api_url = (
            f"https://api-inference.huggingface.co/models/{config.model_name}"
        )
        self.headers = {
            "Authorization": f"Bearer {config.hf_token}",
            "Content-Type": "application/json",
        }

        # Audio buffer for accumulating chunks
        self.audio_buffer = []
        self.buffer_duration = 0.0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def _preprocess_audio(self, audio_data: List[float], sample_rate: int) -> bytes:
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

            # Convert to 16-bit PCM
            audio_int16 = (audio_array * 32767).astype(np.int16)

            return audio_int16.tobytes()

        except Exception as e:
            logger.error(f"Error preprocessing audio: {e}")
            raise

    async def transcribe_chunk(self, audio_chunk: AudioChunk) -> TranscriptionResult:
        """Transcribe a single audio chunk"""
        start_time = time.time()

        try:
            # Preprocess audio
            audio_bytes = self._preprocess_audio(
                audio_chunk.data, audio_chunk.sample_rate
            )

            # Encode audio as base64 for API
            audio_b64 = base64.b64encode(audio_bytes).decode()

            # Prepare payload
            payload = {
                "inputs": audio_b64,
                "parameters": {
                    "return_timestamps": True,
                    "language": "en",  # Can be made configurable
                },
            }

            # Make API request with retries
            for attempt in range(self.config.max_retries):
                try:
                    response = await self.client.post(
                        self.api_url, headers=self.headers, json=payload
                    )

                    if response.status_code == 200:
                        result = response.json()
                        text = result.get("text", "").strip()

                        processing_time = time.time() - start_time

                        return TranscriptionResult(
                            text=text,
                            timestamp=audio_chunk.timestamp,
                            chunk_id=audio_chunk.chunk_id,
                            processing_time=processing_time,
                        )

                    elif response.status_code == 503:
                        # Model loading, wait and retry
                        wait_time = 2**attempt
                        logger.warning(f"Model loading, waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue

                    else:
                        logger.error(
                            f"STT API error: {response.status_code} - {response.text}"
                        )
                        break

                except httpx.TimeoutException:
                    logger.warning(f"STT request timeout, attempt {attempt + 1}")
                    if attempt == self.config.max_retries - 1:
                        raise
                    await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error in transcribe_chunk: {e}")

        # Return empty result on failure
        return TranscriptionResult(
            text="",
            timestamp=audio_chunk.timestamp,
            chunk_id=audio_chunk.chunk_id,
            processing_time=time.time() - start_time,
        )

    def add_audio_to_buffer(
        self, audio_data: List[float], sample_rate: int
    ) -> Optional[AudioChunk]:
        """Add audio data to buffer and return chunk if ready"""
        self.audio_buffer.extend(audio_data)

        # Calculate current buffer duration
        self.buffer_duration = len(self.audio_buffer) / sample_rate

        # Check if we have enough audio for a chunk
        if self.buffer_duration >= self.config.chunk_duration:
            # Extract chunk
            chunk_samples = int(self.config.chunk_duration * sample_rate)
            chunk_data = self.audio_buffer[:chunk_samples]

            # Remove processed data from buffer (with overlap for continuity)
            overlap_samples = int(0.5 * sample_rate)  # 0.5 second overlap
            self.audio_buffer = self.audio_buffer[chunk_samples - overlap_samples :]
            self.buffer_duration = len(self.audio_buffer) / sample_rate

            # Create chunk
            chunk = AudioChunk(
                data=chunk_data,
                sample_rate=sample_rate,
                timestamp=time.time(),
                chunk_id=f"chunk_{len(chunk_data)}_{int(time.time() * 1000)}",
            )

            return chunk

        return None

    async def transcribe_streaming(
        self, audio_stream
    ) -> AsyncGenerator[TranscriptionResult, None]:
        """Transcribe streaming audio data"""
        async for audio_data, sample_rate in audio_stream:
            chunk = self.add_audio_to_buffer(audio_data, sample_rate)
            if chunk:
                result = await self.transcribe_chunk(chunk)
                if result.text:  # Only yield non-empty results
                    yield result

    def flush_buffer(self) -> Optional[AudioChunk]:
        """Flush remaining audio in buffer"""
        if len(self.audio_buffer) > 0:
            chunk = AudioChunk(
                data=self.audio_buffer.copy(),
                sample_rate=self.config.sample_rate,
                timestamp=time.time(),
                chunk_id=f"final_chunk_{int(time.time() * 1000)}",
            )
            self.audio_buffer.clear()
            self.buffer_duration = 0.0
            return chunk
        return None


# Factory function for easy instantiation
async def create_stt_service(
    hf_token: str, model_name: str = "distil-whisper/distil-large-v3.5"
) -> STTService:
    """Create and initialize STT service"""
    config = STTConfig(model_name=model_name, hf_token=hf_token)
    return STTService(config)
