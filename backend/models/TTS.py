import os
import time
import logging
import base64
import io
import asyncio
from typing import Optional, List, Union
from dataclasses import dataclass
from pydantic import BaseModel

import httpx
import numpy as np
from scipy.io import wavfile

logger = logging.getLogger(__name__)

@dataclass
class TTSConfig:
    """Configuration for Text-to-Speech service"""
    model_name: str = "microsoft/speecht5_tts"
    hf_token: Optional[str] = None
    voice_preset: str = "default"
    sample_rate: int = 16000
    max_retries: int = 3
    timeout: float = 30.0
    # Alternative models:
    # "espnet/kan-bayashi_ljspeech_vits" - High quality
    # "facebook/mms-tts-eng" - Multilingual
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
    """Text-to-Speech service using HuggingFace models"""
    
    def __init__(self, config: TTSConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=config.timeout)
        self.api_url = f"https://api-inference.huggingface.co/models/{config.model_name}"
        self.headers = {
            "Authorization": f"Bearer {config.hf_token}",
            "Content-Type": "application/json"
        }
        
        # Cache for voice presets (if model supports multiple voices)
        self.voice_cache = {}
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
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
            "...": ". ",
            "—": " - ",
            "–": " - ",
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Split very long texts into sentences for better processing
        if len(text) > 500:
            # Simple sentence splitting
            sentences = text.replace(". ", ".\n").split("\n")
            # Take first few sentences to stay under limit
            text = ". ".join(sentences[:3]) + "."
        
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
                audio_data
            )
        
        # Normalize audio to prevent clipping
        if np.max(np.abs(audio_data)) > 0:
            audio_data = audio_data / np.max(np.abs(audio_data)) * 0.8
        
        return audio_data
    
    async def synthesize_speech(self, request: TTSRequest) -> TTSResponse:
        """Convert text to speech"""
        start_time = time.time()
        
        try:
            # Preprocess text
            processed_text = self._preprocess_text(request.text)
            logger.info(f"Synthesizing speech for: {processed_text[:100]}...")
            
            # Prepare payload for HuggingFace API
            payload = {
                "inputs": processed_text,
                "parameters": {
                    "vocoder": "hifigan",  # High quality vocoder
                }
            }
            
            # Add voice preset if supported by model
            if request.voice_preset != "default":
                payload["parameters"]["speaker_id"] = request.voice_preset
            
            # Make API request with retries
            for attempt in range(self.config.max_retries):
                try:
                    response = await self.client.post(
                        self.api_url,
                        headers=self.headers,
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        # Handle different response formats
                        content_type = response.headers.get("content-type", "")
                        
                        if "audio" in content_type:
                            # Direct audio response
                            audio_bytes = response.content
                            audio_data = self._parse_audio_bytes(audio_bytes)
                        else:
                            # JSON response with base64 audio
                            result = response.json()
                            if isinstance(result, list) and len(result) > 0:
                                # Handle array response
                                audio_data = np.array(result[0], dtype=np.float32)
                            else:
                                # Handle object response
                                audio_b64 = result.get("audio", "")
                                if audio_b64:
                                    audio_bytes = base64.b64decode(audio_b64)
                                    audio_data = self._parse_audio_bytes(audio_bytes)
                                else:
                                    raise ValueError("No audio data in response")
                        
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
                            text=processed_text
                        )
                    
                    elif response.status_code == 503:
                        # Model loading, wait and retry
                        wait_time = 2 ** attempt
                        logger.warning(f"TTS model loading, waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    else:
                        logger.error(f"TTS API error: {response.status_code} - {response.text}")
                        break
                        
                except httpx.TimeoutException:
                    logger.warning(f"TTS request timeout, attempt {attempt + 1}")
                    if attempt == self.config.max_retries - 1:
                        raise
                    await asyncio.sleep(1)
                    
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
                audio_format="silence"
            )
    
    def _parse_audio_bytes(self, audio_bytes: bytes) -> np.ndarray:
        """Parse audio bytes into numpy array"""
        try:
            # Try to parse as WAV file
            bio = io.BytesIO(audio_bytes)
            sample_rate, audio_data = wavfile.read(bio)
            
            # Convert to float32 and normalize
            if audio_data.dtype == np.int16:
                audio_data = audio_data.astype(np.float32) / 32767.0
            elif audio_data.dtype == np.int32:
                audio_data = audio_data.astype(np.float32) / 2147483647.0
            
            return audio_data
            
        except Exception as e:
            logger.warning(f"Could not parse as WAV, trying raw interpretation: {e}")
            
            # Try to interpret as raw float32 data
            try:
                audio_data = np.frombuffer(audio_bytes, dtype=np.float32)
                return audio_data
            except Exception as e2:
                logger.error(f"Could not parse audio bytes: {e2}")
                # Return silence
                return np.zeros(int(1.0 * self.config.sample_rate))
    
    async def synthesize_batch(self, texts: List[str], session_id: Optional[str] = None) -> List[TTSResponse]:
        """Synthesize multiple texts in batch"""
        responses = []
        
        for text in texts:
            request = TTSRequest(
                text=text,
                session_id=session_id
            )
            response = await self.synthesize_speech(request)
            responses.append(response)
            
            # Small delay between requests to avoid rate limiting
            await asyncio.sleep(0.1)
        
        return responses
    
    def get_supported_voices(self) -> List[str]:
        """Get list of supported voice presets"""
        # This would depend on the specific model
        # For now, return a basic list
        return ["default", "male", "female", "neutral"]
    
    async def test_synthesis(self) -> bool:
        """Test if the TTS service is working"""
        try:
            test_request = TTSRequest(
                text="Hello, this is a test.",
                voice_preset="default"
            )
            
            response = await self.synthesize_speech(test_request)
            return len(response.audio_data) > 0 and response.audio_format != "silence"
            
        except Exception as e:
            logger.error(f"TTS test failed: {e}")
            return False

# Factory function for easy instantiation
async def create_tts_service(hf_token: str, model_name: str = "microsoft/speecht5_tts") -> TTSService:
    """Create and initialize TTS service"""
    config = TTSConfig(
        model_name=model_name,
        hf_token=hf_token
    )
    
    service = TTSService(config)
    
    # Test the service
    try:
        is_working = await service.test_synthesis()
        if is_working:
            logger.info("TTS service initialized successfully")
        else:
            logger.warning("TTS service test failed, but service created")
    except Exception as e:
        logger.error(f"TTS service initialization error: {e}")
        # Don't raise, allow service to be created anyway
    
    return service
