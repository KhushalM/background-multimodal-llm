import os
import logging
from typing import Optional
from dotenv import load_dotenv

from models.STT import STTService, create_stt_service
from models.multimodal import MultimodalService, create_multimodal_service
from models.TTS import TTSService, create_tts_service

# Load environment variables
# Try to load from multiple possible locations
import pathlib

current_dir = pathlib.Path(__file__).parent.parent  # backend directory
env_path = current_dir / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)


class ServiceManager:
    """Manages all AI services (STT, Multimodal with Screen Context, TTS)"""

    def __init__(self):
        self.stt_service: Optional[STTService] = None
        self.multimodal_service: Optional[MultimodalService] = None
        self.tts_service: Optional[TTSService] = None

        # API tokens from environment
        self.gemini_token = os.getenv("GEMINI_API_KEY")
        self.openai_token = os.getenv("OPENAI_API_KEY")

        # Debug environment loading
        logger.debug(f"Environment loading from: {env_path}")
        logger.debug(f"OpenAI key found: {'Yes' if self.openai_token else 'No'}")
        logger.debug(f"Gemini key found: {'Yes' if self.gemini_token else 'No'}")

    async def initialize_services(self):
        """Initialize all AI services"""
        try:
            # Initialize STT service (now uses OpenAI Whisper API)
            if self.openai_token:
                logger.info("Initializing STT service with OpenAI Whisper...")
                self.stt_service = await create_stt_service(model_name="whisper-1")
                await self.stt_service.__aenter__()  # Initialize the service
                logger.info("STT service initialized successfully")
            else:
                logger.warning("OPENAI_API_KEY: " + self.openai_token)
                logger.warning("No OpenAI API key found, STT service not available")

            # Initialize Multimodal service (still needs API key)
            if self.gemini_token:
                logger.info("Initializing Multimodal service with screen context...")
                self.multimodal_service = await create_multimodal_service(api_key=self.gemini_token, model_name="gemini-2.0-flash-exp")
                logger.info("Multimodal service with screen context initialized " "successfully")
            else:
                logger.warning("No Gemini API key found, Multimodal service not available")

            # Initialize TTS service (now uses local pipeline, no token needed)
            logger.info("Initializing TTS service with local pipeline...")
            self.tts_service = await create_tts_service(model_name="microsoft/speecht5_tts")
            await self.tts_service.__aenter__()  # Initialize the pipeline
            logger.info("TTS service initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            raise

    async def cleanup_services(self):
        """Clean up all services"""
        # Clean up STT service
        if self.stt_service:
            try:
                await self.stt_service.__aexit__(None, None, None)
                logger.info("STT service cleaned up successfully")
            except Exception as e:
                logger.error(f"Error cleaning up STT service: {e}")
            finally:
                self.stt_service = None

        # Clean up TTS service
        if self.tts_service:
            try:
                await self.tts_service.__aexit__(None, None, None)
                logger.info("TTS service cleaned up successfully")
            except Exception as e:
                logger.error(f"Error cleaning up TTS service: {e}")
            finally:
                self.tts_service = None

        # Clean up multimodal service (no special cleanup needed)
        if self.multimodal_service:
            self.multimodal_service = None
            logger.info("Multimodal service cleaned up successfully")

    def get_stt_service(self) -> Optional[STTService]:
        """Get the STT service instance"""
        return self.stt_service

    def get_multimodal_service(self) -> Optional[MultimodalService]:
        """Get the Multimodal service instance (includes screen context)"""
        return self.multimodal_service

    def get_tts_service(self) -> Optional[TTSService]:
        """Get the TTS service instance"""
        return self.tts_service

    def is_ready(self) -> bool:
        """Check if essential services are ready"""
        return self.stt_service is not None and self.multimodal_service is not None and self.tts_service is not None

    def is_fully_ready(self) -> bool:
        """Check if all services are ready (same as is_ready since screen context is integrated)"""
        return self.is_ready()


# Global service manager instance
service_manager = ServiceManager()
