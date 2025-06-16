import os
import time
import logging
import base64
import io
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pydantic import BaseModel

import google.generativeai as genai
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class MultimodalConfig:
    """Configuration for Multimodal service with screen context capabilities"""

    model_name: str = "gemini-2.0-flash-exp"
    api_key: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.7
    memory_max_token_limit: int = 2000
    memory_return_messages: bool = True
    # Screen context settings
    max_image_size: int = 1024
    compression_quality: int = 85
    cache_duration: float = 30.0
    system_prompt: str = """You are a helpful AI assistant that can optionally view the user's screen when screen sharing is enabled. 
You have access to conversation history and can provide contextual assistance.

Guidelines:
- Be conversational and friendly
- Reference previous parts of the conversation when relevant
- Keep responses concise but informative
- When screen context is available, use it to provide more relevant assistance
- Mention what you can see on their screen when it helps with your response
- If you see nothing on the screen, say so
- If screen sharing is not enabled and the user asks about their screen, 
  clearly state that screen sharing is not enabled and ask them to enable it
- NEVER hallucinate or make up screen content when no screen is shared
"""


class ConversationInput(BaseModel):
    """Input for conversation processing"""

    text: str
    user_id: str = "default"
    session_id: str = "default"
    timestamp: float
    context: Optional[Dict[str, Any]] = None
    screen_image: Optional[str] = None  # base64 encoded image


class ConversationResponse(BaseModel):
    """Response from conversation processing"""

    text: str
    timestamp: float
    processing_time: float
    session_id: str
    token_count: Optional[int] = None
    screen_context: Optional[Dict[str, Any]] = None


class MultimodalService:
    """Main multimodal service using Gemini with integrated screen context"""

    def __init__(self, config: MultimodalConfig):
        self.config = config

        # Initialize single Gemini multimodal model
        if config.api_key:
            genai.configure(api_key=config.api_key)
            self.model = genai.GenerativeModel(config.model_name)
            logger.info(f"Gemini model {config.model_name} initialized")
        else:
            self.model = None
            logger.warning("No Gemini API key provided")

        # Initialize memory for different sessions
        self.session_memories: Dict[str, List[Dict[str, Any]]] = {}

        # Screen context cache
        self.screen_cache: Dict[str, Any] = {}

    def _get_or_create_memory(self, session_id: str) -> List[Dict[str, Any]]:
        """Get or create memory for a session"""
        if session_id not in self.session_memories:
            self.session_memories[session_id] = []
            logger.info(f"Created new memory for session: {session_id}")
        return self.session_memories[session_id]

    def _decode_image(self, base64_data: str) -> Optional[Image.Image]:
        """Decode base64 image data"""
        try:
            # Remove data URL prefix if present
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]

            image_bytes = base64.b64decode(base64_data)
            image = Image.open(io.BytesIO(image_bytes))

            # Convert to RGB if necessary
            if image.mode != "RGB":
                image = image.convert("RGB")

            return image

        except Exception as e:
            logger.error(f"Error decoding image: {e}")
            return None

    def _resize_image(self, image: Image.Image) -> Image.Image:
        """Resize image to fit within max dimensions"""
        width, height = image.size
        max_size = self.config.max_image_size

        if width <= max_size and height <= max_size:
            return image

        # Calculate new dimensions maintaining aspect ratio
        if width > height:
            new_width = max_size
            new_height = int(height * max_size / width)
        else:
            new_height = max_size
            new_width = int(width * max_size / height)

        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def _build_conversation_context(
        self, session_id: str, current_text: str
    ) -> List[str]:
        """Build conversation context from memory"""
        memory = self._get_or_create_memory(session_id)
        context_parts = [self.config.system_prompt]

        # Add recent conversation history (last 5 exchanges)
        recent_memory = memory[-10:] if len(memory) > 10 else memory
        for entry in recent_memory:
            if entry["type"] == "user":
                context_parts.append(f"User: {entry['content']}")
            elif entry["type"] == "assistant":
                context_parts.append(f"Assistant: {entry['content']}")

        # Add current user input
        context_parts.append(f"User: {current_text}")

        return context_parts

    async def process_conversation(
        self, input_data: ConversationInput
    ) -> ConversationResponse:
        """Process a conversation turn with optional screen context"""
        start_time = time.time()

        try:
            if not self.model:
                return ConversationResponse(
                    text="Sorry, the AI service is not available. "
                    "Please check the API configuration.",
                    timestamp=input_data.timestamp,
                    processing_time=time.time() - start_time,
                    session_id=input_data.session_id,
                )

            # Build conversation context
            context_parts = self._build_conversation_context(
                input_data.session_id, input_data.text
            )

            # Prepare content for Gemini (text + optional image)
            content = ["\n".join(context_parts)]

            # Handle screen image if provided
            screen_context_data = None

            if input_data.screen_image:
                # Screen image was provided - use it
                image = self._decode_image(input_data.screen_image)
                if image:
                    image = self._resize_image(image)
                    content.append(image)

                    screen_context_data = {
                        "has_screen_context": True,
                        "image_size": image.size,
                        "capture_method": "provided",
                    }

                    content[0] += (
                        "\n\nScreen sharing is ENABLED. I can see your screen. "
                        "I'll analyze what's shown and provide contextual "
                        "assistance based on both our conversation and what I can see."
                    )
                else:
                    content[0] += (
                        "\n\nScreen sharing was attempted but the image could not be processed. "
                        "Screen sharing is effectively OFF."
                    )
            else:
                # No screen image provided - explicitly tell AI
                content[0] += (
                    "\n\nScreen sharing is currently OFF/DISABLED. I cannot see "
                    "the user's screen. Do not make up or hallucinate screen content."
                )

            logger.info(f"Processing conversation for session {input_data.session_id}")

            if input_data.screen_image:
                logger.info("Screen context provided in request")

            # Generate response using single multimodal call
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.model.generate_content(content)
            )

            response_text = (
                response.text
                if response.text
                else "I apologize, but I couldn't generate a response."
            )

            # Save to memory
            memory = self._get_or_create_memory(input_data.session_id)
            memory.append(
                {
                    "type": "user",
                    "content": input_data.text,
                    "timestamp": input_data.timestamp,
                    "has_screen": bool(input_data.screen_image),
                }
            )
            memory.append(
                {
                    "type": "assistant",
                    "content": response_text,
                    "timestamp": time.time(),
                }
            )

            # Keep memory manageable (last 50 entries)
            if len(memory) > 50:
                memory[:] = memory[-50:]

            processing_time = time.time() - start_time

            logger.info(f"Generated response in {processing_time:.2f}s")
            logger.debug(f"Response: {response_text[:100]}...")

            return ConversationResponse(
                text=response_text,
                timestamp=input_data.timestamp,
                processing_time=processing_time,
                session_id=input_data.session_id,
                token_count=len(response_text.split()),
                screen_context=screen_context_data,
            )

        except Exception as e:
            logger.error(f"Error processing conversation: {e}")

            return ConversationResponse(
                text=(
                    "I apologize, but I encountered an error processing "
                    "your request. Please try again."
                ),
                timestamp=input_data.timestamp,
                processing_time=time.time() - start_time,
                session_id=input_data.session_id,
            )

    def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        return self._get_or_create_memory(session_id)

    def clear_session_memory(self, session_id: str) -> bool:
        """Clear memory for a specific session"""
        if session_id in self.session_memories:
            del self.session_memories[session_id]
            logger.info(f"Cleared memory for session: {session_id}")
            return True
        return False

    def get_session_summary(self, session_id: str) -> Optional[str]:
        """Get a summary of the conversation for a session"""
        memory = self._get_or_create_memory(session_id)
        if not memory:
            return None

        # Simple summary of recent activity
        recent_exchanges = len([m for m in memory[-10:] if m["type"] == "user"])
        return f"Recent conversation with {recent_exchanges} user messages"

    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        return list(self.session_memories.keys())

    def clear_screen_cache(self):
        """Clear screen analysis cache"""
        self.screen_cache.clear()
        logger.info("Screen cache cleared")


# Factory function
async def create_multimodal_service(
    api_key: str, model_name: str = "gemini-2.0-flash-exp"
) -> MultimodalService:
    """Create and initialize multimodal service with screen context capabilities"""
    config = MultimodalConfig(
        model_name=model_name,
        api_key=api_key,
    )

    service = MultimodalService(config)

    # Test the connection
    try:
        test_input = ConversationInput(
            text="Hello, this is a connection test.",
            timestamp=time.time(),
            session_id="test_session",
        )

        response = await service.process_conversation(test_input)
        if response.text and "error" not in response.text.lower():
            logger.info(
                "Multimodal service with screen context initialized successfully"
            )
            # Clean up test session
            service.clear_session_memory("test_session")
        else:
            logger.warning("Multimodal service test returned error response")

    except Exception as e:
        logger.error(f"Failed to initialize multimodal service: {e}")
        raise

    return service
