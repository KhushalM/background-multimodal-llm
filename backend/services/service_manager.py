import os
import logging
from typing import Optional
from dotenv import load_dotenv

from models.STT import STTService, create_stt_service
from models.multimodal import MultimodalService, create_multimodal_service
from models.TTS import TTSService, create_tts_service

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class ServiceManager:
    """Manages all AI services (STT, Multimodal, TTS)"""
    
    def __init__(self):
        self.stt_service: Optional[STTService] = None
        self.multimodal_service: Optional[MultimodalService] = None
        self.tts_service: Optional[TTSService] = None
        
        # API tokens from environment
        self.hf_token = os.getenv("HUGGINGFACE_API_TOKEN")
        self.gemini_token = os.getenv("GEMINI_API_KEY")
        
    async def initialize_services(self):
        """Initialize all AI services"""
        try:
            # Initialize STT service
            if self.hf_token:
                logger.info("Initializing STT service...")
                self.stt_service = await create_stt_service(
                    hf_token=self.hf_token,
                    model_name="openai/whisper-large-v3"
                )
                logger.info("STT service initialized successfully")
            else:
                logger.warning("No HuggingFace token found, STT service not available")
                
            # Initialize Multimodal service
            if self.gemini_token:
                logger.info("Initializing Multimodal service...")
                self.multimodal_service = await create_multimodal_service(
                    api_key=self.gemini_token,
                    model_name="gemini-1.5-flash"
                )
                logger.info("Multimodal service initialized successfully")
            else:
                logger.warning("No Gemini API key found, Multimodal service not available")
                
            # Initialize TTS service
            if self.hf_token:
                logger.info("Initializing TTS service...")
                self.tts_service = await create_tts_service(
                    hf_token=self.hf_token,
                    model_name="microsoft/speecht5_tts"
                )
                logger.info("TTS service initialized successfully")
            else:
                logger.warning("No HuggingFace token found, TTS service not available")
            
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            raise
    
    async def cleanup_services(self):
        """Clean up all services"""
        if self.stt_service:
            await self.stt_service.__aexit__(None, None, None)
        if self.tts_service:
            await self.tts_service.__aexit__(None, None, None)
            
    def get_stt_service(self) -> Optional[STTService]:
        """Get the STT service instance"""
        return self.stt_service
    
    def get_multimodal_service(self) -> Optional[MultimodalService]:
        """Get the Multimodal service instance"""
        return self.multimodal_service
    
    def get_tts_service(self) -> Optional[TTSService]:
        """Get the TTS service instance"""
        return self.tts_service
    
    def is_ready(self) -> bool:
        """Check if essential services are ready"""
        return (self.stt_service is not None and 
                self.multimodal_service is not None and 
                self.tts_service is not None)

# Global service manager instance
service_manager = ServiceManager() 