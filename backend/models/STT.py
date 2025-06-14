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
    chunk_duration: float = 4.0  # increased from 2.0 to reduce multiple chunks
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


class STTService:
    """Speech-to-Text service using HuggingFace Transformers pipeline"""

    def __init__(self, config: STTConfig):
        self.config = config
        self.pipeline = None
        self.device = self._get_device()
        self.torch_dtype = self._get_torch_dtype()

        # Audio buffer for accumulating chunks
        self.audio_buffer = []
        self.buffer_duration = 0.0

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

            logger.debug(f"Transcribed audio chunk: '{text}' in {processing_time:.2f}s")

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

            # Remove processed data from buffer (with minimal overlap for continuity)
            overlap_samples = int(
                0.2 * sample_rate
            )  # 0.2 second overlap - reduced from 0.5
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
    model_name: str = "distil-whisper/distil-large-v3.5", **config_kwargs
) -> STTService:
    """Create and initialize STT service"""
    config = STTConfig(model_name=model_name, **config_kwargs)
    return STTService(config)
