import os
import time
import logging
import io
import asyncio
from typing import Optional, List, Union
from dataclasses import dataclass
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor

import torch
import numpy as np
from transformers import (
    pipeline,
    SpeechT5Processor,
    SpeechT5ForTextToSpeech,
    SpeechT5HifiGan,
)
from datasets import load_dataset
import soundfile as sf

logger = logging.getLogger(__name__)


@dataclass
class TTSConfig:
    """Configuration for Text-to-Speech service"""

    model_name: str = "microsoft/speecht5_tts"
    vocoder_name: str = "microsoft/speecht5_hifigan"
    device: str = "auto"  # "auto", "cpu", "cuda", or "mps"
    torch_dtype: str = "auto"  # "auto", "float16", "float32"
    voice_preset: str = "default"
    sample_rate: int = 16000
    max_retries: int = 3
    # Alternative models:
    # "microsoft/speecht5_tts" - Good balance of quality and speed
    # "facebook/mms-tts-eng" - Multilingual support
    # "suno/bark" - Very natural but slower


class TTSRequest(BaseModel):
    """Request for text-to-speech conversion"""

    text: str
    voice_preset: str = "default"
    speed: float = 1.0
    pitch: float = 1.0
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
    """Text-to-Speech service using HuggingFace Transformers pipeline"""

    def __init__(self, config: TTSConfig):
        self.config = config
        self.device = self._get_device()
        self.torch_dtype = self._get_torch_dtype()

        # Create dedicated ThreadPoolExecutor to avoid semaphore leaks
        # Use thread_name_prefix and ensure proper cleanup
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tts", initializer=None, initargs=())

        # Pipeline components
        self.model = None
        self.processor = None
        self.vocoder = None
        self.speaker_embeddings = None

        logger.info(f"TTS service initialized with device: {self.device}, dtype: {self.torch_dtype}")

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
            logger.info(f"Loading TTS model: {self.config.model_name}")

            # Load processor
            self.processor = SpeechT5Processor.from_pretrained(self.config.model_name)

            # Load model
            self.model = SpeechT5ForTextToSpeech.from_pretrained(self.config.model_name, torch_dtype=self.torch_dtype)
            self.model.to(self.device)

            # Load vocoder
            self.vocoder = SpeechT5HifiGan.from_pretrained(self.config.vocoder_name, torch_dtype=self.torch_dtype)
            self.vocoder.to(self.device)

            # Load speaker embeddings dataset with fallback
            try:
                embeddings_dataset = load_dataset("Matthijs/cmu-arctic-xvectors", split="validation", download_mode="force_redownload", cache_dir=None)
                speaker_embeddings = torch.tensor(embeddings_dataset[7306]["xvector"]).unsqueeze(0)
                self.speaker_embeddings = speaker_embeddings.to(self.device)
                logger.info("Loaded speaker embeddings from dataset")
            except Exception as e:
                logger.warning(f"Failed to load speaker embeddings: {e}")
                logger.info("Using default speaker embeddings")
                # Create default speaker embedding (512-dim vector for SpeechT5)
                # Based on typical xvector embedding size for SpeechT5
                default_embedding = torch.randn(1, 512, dtype=self.torch_dtype)
                self.speaker_embeddings = default_embedding.to(self.device)

            logger.info("TTS pipeline loaded successfully")

        except Exception as e:
            logger.error(f"Error loading TTS pipeline: {e}")
            raise

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup resources"""
        if self.model is not None:
            # Clear CUDA cache if using GPU
            if self.device == "cuda":
                torch.cuda.empty_cache()
            self.model = None
            self.processor = None
            self.vocoder = None
            self.speaker_embeddings = None

        # Shutdown the executor to prevent semaphore leaks
        if hasattr(self, "executor") and self.executor:
            try:
                # First try immediate shutdown, then wait
                self.executor.shutdown(wait=False)
                self.executor.shutdown(wait=True)
            except Exception as e:
                logger.warning(f"Error shutting down TTS executor: {e}")
            finally:
                self.executor = None

    def _get_token_count(self, text: str) -> int:
        """Estimate token count for the text"""
        if self.processor:
            try:
                # Use the actual tokenizer for accurate count
                inputs = self.processor(text=text, return_tensors="pt")
                return inputs["input_ids"].shape[1]
            except:
                pass

        # Fallback: rough estimate (1 token ≈ 4 characters)
        return len(text) // 4

    def _preprocess_text(self, text: str) -> str:
        """Clean and prepare text for TTS with token limit awareness"""
        # Remove or replace problematic characters
        text = text.strip()

        # Handle common replacements for better pronunciation
        replacements = {
            "&": "and",
            "@": "at",
            "#": "hashtag",
            "$": "dollar",
            "%": "percent",
            "...": ". ",
            "—": " - ",
            "–": " - ",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        # SpeechT5 has a maximum token limit of 600 tokens
        max_tokens = 550  # Leave some buffer

        # Check token count and truncate if necessary
        if self._get_token_count(text) > max_tokens:
            # Simple sentence splitting
            sentences = text.replace(". ", ".\n").split("\n")

            # Build text up to token limit
            result_text = ""
            for sentence in sentences:
                test_text = result_text + sentence + ". "
                if self._get_token_count(test_text) > max_tokens:
                    break
                result_text = test_text

            # If we got at least one sentence, use it
            if result_text.strip():
                text = result_text.strip()
            else:
                # Fallback: truncate by characters
                # Rough estimate: 550 tokens * 4 chars/token = 2200 chars
                max_chars = 2200
                text = text[:max_chars].rsplit(" ", 1)[0] + "."

        return text

    def _postprocess_audio(self, audio_data: np.ndarray, target_sample_rate: int = None) -> np.ndarray:
        """Post-process audio data"""
        if target_sample_rate and target_sample_rate != self.config.sample_rate:
            # Simple resampling
            ratio = target_sample_rate / self.config.sample_rate
            new_length = int(len(audio_data) * ratio)
            audio_data = np.interp(
                np.linspace(0, len(audio_data) - 1, new_length),
                np.arange(len(audio_data)),
                audio_data,
            )

        # Normalize audio to prevent clipping
        if np.max(np.abs(audio_data)) > 0:
            audio_data = audio_data / np.max(np.abs(audio_data)) * 0.8

        return audio_data

    async def synthesize_speech(self, request: TTSRequest) -> TTSResponse:
        """Convert text to speech"""
        start_time = time.time()

        try:
            if self.model is None or self.processor is None:
                raise RuntimeError("TTS pipeline not initialized. Use 'async with' context manager.")

            # Preprocess text
            processed_text = self._preprocess_text(request.text)
            logger.info(f"Synthesizing speech for: {processed_text[:100]}...")

            # Run in dedicated executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            audio_data = await loop.run_in_executor(self.executor, self._generate_speech, processed_text)

            # Post-process audio
            audio_data = self._postprocess_audio(audio_data)
            duration = len(audio_data) / self.config.sample_rate
            processing_time = time.time() - start_time

            logger.info(f"Generated {duration:.2f}s of audio in {processing_time:.2f}s")

            return TTSResponse(
                audio_data=audio_data.tolist(),
                sample_rate=self.config.sample_rate,
                duration=duration,
                processing_time=processing_time,
                text=processed_text,
            )

        except Exception as e:
            logger.error(f"Error in synthesize_speech: {e}")

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

    def _generate_speech(self, text: str) -> np.ndarray:
        """Generate speech from text using the loaded model"""
        # Tokenize text
        inputs = self.processor(text=text, return_tensors="pt")
        input_ids = inputs["input_ids"].to(self.device)

        # Generate speech with the model
        with torch.no_grad():
            speech = self.model.generate_speech(input_ids, self.speaker_embeddings, vocoder=self.vocoder)

        # Convert to numpy and ensure it's on CPU
        speech_np = speech.cpu().numpy()

        return speech_np

    async def synthesize_batch(self, texts: List[str], session_id: Optional[str] = None) -> List[TTSResponse]:
        """Synthesize multiple texts in batch"""
        responses = []

        for text in texts:
            request = TTSRequest(text=text, session_id=session_id)
            response = await self.synthesize_speech(request)
            responses.append(response)

            # Small delay between requests to manage memory
            await asyncio.sleep(0.1)

        return responses

    def get_supported_voices(self) -> List[str]:
        """Get list of supported voice presets"""
        # For SpeechT5, we use different speaker embeddings
        # In a full implementation, you could load different embeddings
        return ["default", "male", "female", "neutral"]

    async def test_synthesis(self) -> bool:
        """Test if the TTS service is working"""
        try:
            test_request = TTSRequest(text="Hello, this is a test.", voice_preset="default")

            response = await self.synthesize_speech(test_request)
            return len(response.audio_data) > 0 and response.audio_format != "silence"

        except Exception as e:
            logger.error(f"TTS test failed: {e}")
            return False


# Factory function for easy instantiation
async def create_tts_service(model_name: str = "microsoft/speecht5_tts", **config_kwargs) -> TTSService:
    """Create and initialize TTS service"""
    config = TTSConfig(model_name=model_name, **config_kwargs)

    service = TTSService(config)

    # Test the service
    try:
        async with service:
            is_working = await service.test_synthesis()
            if is_working:
                logger.info("TTS service initialized successfully")
            else:
                logger.warning("TTS service test failed, but service created")
    except Exception as e:
        logger.error(f"TTS service initialization error: {e}")
        # Don't raise, allow service to be created anyway

    return service
