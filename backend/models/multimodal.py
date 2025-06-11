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
from langchain.memory import ConversationSummaryBufferMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class MultimodalConfig:
    """Configuration for Multimodal service with screen context capabilities"""
    model_name: str = "gemini-2.0-flash-exp"
    vision_model: str = "gemini-2.0-flash-exp"
    api_key: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.7
    memory_max_token_limit: int = 2000
    memory_return_messages: bool = True
    # Screen context settings
    max_image_size: int = 1024
    compression_quality: int = 85
    analysis_interval: float = 2.0
    cache_duration: float = 30.0
    system_prompt: str = """You are a helpful AI assistant with access to the user's screen and conversation history. 
You can see what they're working on and provide contextual assistance.

Guidelines:
- Be conversational and friendly
- Reference previous parts of the conversation when relevant
- If you notice patterns in what they're asking, point them out helpfully
- Keep responses concise but informative
- Ask clarifying questions when needed
- When screen context is available, use it to provide more relevant assistance
- Mention what you can see on their screen when it helps with your response
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

class ScreenCapture(BaseModel):
    """Screen capture data"""
    image_data: str  # base64 encoded
    timestamp: float
    width: int
    height: int
    format: str = "JPEG"

class ScreenAnalysis(BaseModel):
    """Analysis of screen content"""
    description: str
    elements: List[str]
    context_type: str  # "code", "document", "browser", "terminal", "design", "general"
    confidence: float
    timestamp: float
    processing_time: float

class MultimodalService:
    """Main multimodal service using Gemini + LangChain memory with integrated screen context"""
    
    def __init__(self, config: MultimodalConfig):
        self.config = config
        
        # Initialize Gemini for text
        if config.api_key:
            genai.configure(api_key=config.api_key)
            self.llm = ChatGoogleGenerativeAI(
                model=config.model_name,
                google_api_key=config.api_key,
                temperature=config.temperature,
                max_tokens=config.max_tokens
            )
            # Initialize Gemini Vision for screen analysis
            self.vision_model = genai.GenerativeModel(config.vision_model)
        else:
            self.llm = None
            self.vision_model = None
            logger.warning("No Gemini API key provided")
        
        # Initialize memory for different sessions
        self.session_memories: Dict[str, ConversationSummaryBufferMemory] = {}
        
        # Screen context cache
        self.screen_analysis_cache: Dict[str, ScreenAnalysis] = {}
        
        # Create prompt template
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", config.system_prompt),
            ("placeholder", "{history}"),
            ("human", "{input}")
        ])
        
    def _get_or_create_memory(self, session_id: str) -> ConversationSummaryBufferMemory:
        """Get or create memory for a session"""
        if session_id not in self.session_memories:
            self.session_memories[session_id] = ConversationSummaryBufferMemory(
                llm=self.llm,
                max_token_limit=self.config.memory_max_token_limit,
                return_messages=self.config.memory_return_messages
            )
            logger.info(f"Created new memory for session: {session_id}")
        
        return self.session_memories[session_id]
    
    async def analyze_screen_image(self, image_data: str) -> Optional[ScreenAnalysis]:
        """Analyze screen image using Gemini Vision"""
        if not self.vision_model:
            return None
            
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(image_data)
            if cache_key in self.screen_analysis_cache:
                cached_analysis = self.screen_analysis_cache[cache_key]
                if time.time() - cached_analysis.timestamp < self.config.cache_duration:
                    logger.debug("Using cached screen analysis")
                    return cached_analysis
            
            # Decode and process image
            image = self._decode_image(image_data)
            if not image:
                return None
            
            # Resize if necessary
            image = self._resize_image(image)
            
            logger.info("Analyzing screen content with Gemini Vision...")
            
            # Create analysis prompt
            prompt = self._create_screen_analysis_prompt()
            
            # Analyze with Gemini Vision
            response = await self._analyze_with_gemini_vision(image, prompt)
            
            # Parse response
            analysis = self._parse_screen_analysis_response(response, time.time())
            analysis.processing_time = time.time() - start_time
            
            # Cache the result
            self.screen_analysis_cache[cache_key] = analysis
            
            logger.info(f"Screen analysis completed in {analysis.processing_time:.2f}s")
            logger.debug(f"Context: {analysis.context_type}, Elements: {len(analysis.elements)}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing screen: {e}")
            return None
    
    def _decode_image(self, base64_data: str) -> Optional[Image.Image]:
        """Decode base64 image data"""
        try:
            # Remove data URL prefix if present
            if ',' in base64_data:
                base64_data = base64_data.split(',')[1]
            
            image_bytes = base64.b64decode(base64_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
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
    
    def _create_screen_analysis_prompt(self) -> str:
        """Create prompt for screen analysis"""
        return """Analyze this screenshot and provide:

1. A brief description of what's shown (2-3 sentences)
2. Key UI elements or content visible
3. The type of context (choose one: code, document, browser, terminal, design, general)
4. Your confidence level (0.0-1.0)

Focus on:
- Programming/development content
- Text content that might be relevant for assistance
- Applications and tools being used
- Current workflow or task

Respond in this format:
DESCRIPTION: [brief description]
ELEMENTS: [comma-separated list of key elements]
CONTEXT_TYPE: [code/document/browser/terminal/design/general]
CONFIDENCE: [0.0-1.0]"""
    
    async def _analyze_with_gemini_vision(self, image: Image.Image, prompt: str) -> str:
        """Analyze image with Gemini Vision model"""
        try:
            # Convert PIL image to bytes for Gemini
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='JPEG', quality=self.config.compression_quality)
            img_buffer.seek(0)
            
            # Create Gemini input
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.vision_model.generate_content([prompt, image])
            )
            
            return response.text if response.text else "No analysis generated"
            
        except Exception as e:
            logger.error(f"Error calling Gemini Vision: {e}")
            return f"Vision analysis error: {str(e)}"
    
    def _parse_screen_analysis_response(self, response: str, timestamp: float) -> ScreenAnalysis:
        """Parse Gemini response into structured analysis"""
        try:
            lines = response.strip().split('\n')
            
            description = "No description available"
            elements = []
            context_type = "general"
            confidence = 0.5
            
            for line in lines:
                line = line.strip()
                if line.startswith('DESCRIPTION:'):
                    description = line[12:].strip()
                elif line.startswith('ELEMENTS:'):
                    elements_str = line[9:].strip()
                    elements = [e.strip() for e in elements_str.split(',') if e.strip()]
                elif line.startswith('CONTEXT_TYPE:'):
                    context_type = line[13:].strip().lower()
                elif line.startswith('CONFIDENCE:'):
                    try:
                        confidence = float(line[11:].strip())
                    except ValueError:
                        confidence = 0.5
            
            return ScreenAnalysis(
                description=description,
                elements=elements,
                context_type=context_type,
                confidence=confidence,
                timestamp=timestamp,
                processing_time=0.0  # Set by caller
            )
            
        except Exception as e:
            logger.warning(f"Error parsing analysis response: {e}")
            
            # Fallback: use raw response as description
            return ScreenAnalysis(
                description=response[:200] + "..." if len(response) > 200 else response,
                elements=[],
                context_type="general",
                confidence=0.3,
                timestamp=timestamp,
                processing_time=0.0
            )
    
    def _generate_cache_key(self, image_data: str) -> str:
        """Generate cache key for screen image"""
        # Simple hash based on image data length and current time interval
        interval_timestamp = int(time.time() / self.config.analysis_interval)
        return f"{len(image_data)}_{interval_timestamp}"

    async def process_conversation(self, input_data: ConversationInput) -> ConversationResponse:
        """Process a conversation turn with optional screen context"""
        start_time = time.time()
        
        try:
            if not self.llm:
                return ConversationResponse(
                    text="Sorry, the AI service is not available right now. Please check the API configuration.",
                    timestamp=input_data.timestamp,
                    processing_time=time.time() - start_time,
                    session_id=input_data.session_id
                )
            
            # Analyze screen image if provided
            screen_analysis = None
            if input_data.screen_image:
                screen_analysis = await self.analyze_screen_image(input_data.screen_image)
            
            # Get memory for this session
            memory = self._get_or_create_memory(input_data.session_id)
            
            # Get conversation history
            history = memory.chat_memory.messages
            
            # Build the prompt with enhanced context
            prompt_input = {
                "history": history,
                "input": input_data.text
            }
            
            # Enhanced context formatting with screen analysis
            context_parts = []
            
            # Add screen context if available
            if screen_analysis:
                screen_context = f"Screen Analysis: {screen_analysis.description}"
                if screen_analysis.elements:
                    screen_context += f" | UI Elements: {', '.join(screen_analysis.elements[:5])}"  # Limit to first 5
                screen_context += f" | Context Type: {screen_analysis.context_type}"
                context_parts.append(screen_context)
            
            # Add traditional context
            if input_data.context:
                traditional_context = self._format_context(input_data.context)
                if traditional_context != "No additional context":
                    context_parts.append(traditional_context)
            
            # Combine all context
            if context_parts:
                full_context = " | ".join(context_parts)
                prompt_input["input"] = f"Context: {full_context}\n\nUser: {input_data.text}"
            
            logger.info(f"Processing conversation for session {input_data.session_id}")
            if screen_analysis:
                logger.info(f"Screen context: {screen_analysis.context_type} - {screen_analysis.description[:100]}")
            logger.debug(f"Input: {input_data.text}")
            
            # Generate response using LangChain
            formatted_prompt = self.prompt_template.format_messages(**prompt_input)
            response = await self.llm.ainvoke(formatted_prompt)
            
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Save to memory
            memory.save_context(
                {"input": input_data.text},
                {"output": response_text}
            )
            
            processing_time = time.time() - start_time
            
            logger.info(f"Generated response in {processing_time:.2f}s")
            logger.debug(f"Response: {response_text}")
            
            # Prepare screen context for response
            screen_context_data = None
            if screen_analysis:
                screen_context_data = {
                    "description": screen_analysis.description,
                    "context_type": screen_analysis.context_type,
                    "confidence": screen_analysis.confidence,
                    "elements": screen_analysis.elements
                }
            
            return ConversationResponse(
                text=response_text,
                timestamp=input_data.timestamp,
                processing_time=processing_time,
                session_id=input_data.session_id,
                token_count=len(response_text.split()),  # Simple token estimate
                screen_context=screen_context_data
            )
            
        except Exception as e:
            logger.error(f"Error processing conversation: {e}")
            
            return ConversationResponse(
                text=f"I apologize, but I encountered an error processing your request. Please try again.",
                timestamp=input_data.timestamp,
                processing_time=time.time() - start_time,
                session_id=input_data.session_id
            )
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context information for the prompt"""
        context_parts = []
        
        if "screen_info" in context:
            context_parts.append(f"Screen: {context['screen_info']}")
        
        if "app_info" in context:
            context_parts.append(f"Current app: {context['app_info']}")
        
        if "time_info" in context:
            context_parts.append(f"Time: {context['time_info']}")
        
        return " | ".join(context_parts) if context_parts else "No additional context"
    
    def get_conversation_history(self, session_id: str) -> List[BaseMessage]:
        """Get conversation history for a session"""
        if session_id in self.session_memories:
            return self.session_memories[session_id].chat_memory.messages
        return []
    
    def clear_session_memory(self, session_id: str) -> bool:
        """Clear memory for a specific session"""
        if session_id in self.session_memories:
            del self.session_memories[session_id]
            logger.info(f"Cleared memory for session: {session_id}")
            return True
        return False
    
    def get_session_summary(self, session_id: str) -> Optional[str]:
        """Get a summary of the conversation for a session"""
        if session_id in self.session_memories:
            memory = self.session_memories[session_id]
            if hasattr(memory, 'moving_summary_buffer') and memory.moving_summary_buffer:
                return memory.moving_summary_buffer
        return None
    
    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        return list(self.session_memories.keys())
    
    def clear_screen_cache(self):
        """Clear screen analysis cache"""
        self.screen_analysis_cache.clear()
        logger.info("Screen analysis cache cleared")

# Factory function
async def create_multimodal_service(api_key: str, model_name: str = "gemini-2.0-flash-exp") -> MultimodalService:
    """Create and initialize multimodal service with screen context capabilities"""
    config = MultimodalConfig(
        model_name=model_name,
        vision_model=model_name,  # Use same model for vision
        api_key=api_key
    )
    
    service = MultimodalService(config)
    
    # Test the connection
    try:
        test_input = ConversationInput(
            text="Hello, this is a connection test.",
            timestamp=time.time(),
            session_id="test_session"
        )
        
        response = await service.process_conversation(test_input)
        if response.text and "error" not in response.text.lower():
            logger.info("Multimodal service with screen context initialized successfully")
            # Clean up test session
            service.clear_session_memory("test_session")
        else:
            logger.warning("Multimodal service test returned error response")
            
    except Exception as e:
        logger.error(f"Failed to initialize multimodal service: {e}")
        raise
    
    return service
