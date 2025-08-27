"""
Enhanced Multimodal Service with DSPy + LangGraph Tool Calling
Integrates the enhanced tool calling system with the existing multimodal pipeline.
"""

import time
import logging
import base64
import io
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import google.generativeai as genai
from PIL import Image

from .enhanced_tool_calling import EnhancedToolCallingService, create_enhanced_tool_calling_service
from .multimodal import MultimodalConfig, ConversationInput, ConversationResponse

logger = logging.getLogger(__name__)


@dataclass
class EnhancedMultimodalConfig(MultimodalConfig):
    """Enhanced configuration that includes DSPy + LangGraph settings"""

    # Enhanced tool calling settings
    enable_enhanced_tool_calling: bool = True
    tool_calling_confidence_threshold: float = 0.7
    max_tool_retries: int = 2
    quality_score_threshold: float = 0.6

    # DSPy optimization settings
    enable_dspy_optimization: bool = True
    optimization_metric: str = "quality_score"  # quality_score, success_rate, response_time

    system_prompt: str = """You are a helpful AI assistant with enhanced reasoning capabilities. 
You have access to powerful research tools and can analyze screen content when available.

Enhanced Tool Calling Guidelines:
- You now use an intelligent tool calling system powered by DSPy and LangGraph
- Tool selection and parameter optimization are automatically handled
- When you need external information, the system will intelligently decide the best approach
- You can access web research, deep analysis, and reasoning capabilities through Perplexity
- All tool calls are optimized for better results and higher quality responses

Conversation Guidelines:
- Be conversational and friendly
- Reference previous parts of the conversation when relevant
- When screen context is available, use it to provide more relevant assistance
- If you need to search for information, the enhanced system will handle it optimally
- Provide clear, well-structured responses with proper citations when available

Available enhanced tools: {tools}
"""


class EnhancedMultimodalService:
    """Enhanced multimodal service with DSPy + LangGraph tool calling"""

    def __init__(self, config: EnhancedMultimodalConfig):
        self.config = config

        # Initialize Gemini model
        if config.api_key:
            genai.configure(api_key=config.api_key)
            self.model = genai.GenerativeModel(config.model_name)
            logger.info(f"Gemini model {config.model_name} initialized")
        else:
            self.model = None
            logger.warning("No Gemini API key provided")

        # Initialize enhanced tool calling service
        self.enhanced_tool_service: Optional[EnhancedToolCallingService] = None

        # Initialize memory for different sessions
        self.session_memories: Dict[str, List[Dict[str, Any]]] = {}

        # Screen context cache
        self.screen_cache: Dict[str, Any] = {}

        # Available tools (will be populated)
        self.available_tools = []

        # Performance metrics
        self.performance_metrics = {"total_requests": 0, "tool_requests": 0, "successful_tool_calls": 0, "average_quality_score": 0.0, "average_response_time": 0.0}

    async def _initialize_enhanced_tools(self):
        """Initialize enhanced tool calling service"""
        try:
            if self.config.enable_enhanced_tool_calling and self.config.api_key:
                self.enhanced_tool_service = await create_enhanced_tool_calling_service(gemini_api_key=self.config.api_key)

                # Get available tools
                await self.enhanced_tool_service.perplexity_client.connect()
                tools_result = await self.enhanced_tool_service.perplexity_client.list_tools()
                self.available_tools = tools_result if tools_result else []

                if self.available_tools:
                    logger.info(f"Enhanced tool calling initialized with tools: {self.available_tools}")
                else:
                    logger.warning("No tools available for enhanced tool calling")

            else:
                logger.info("Enhanced tool calling disabled or no API key available")

        except Exception as e:
            logger.error(f"Failed to initialize enhanced tool calling: {e}")
            self.enhanced_tool_service = None

    def _get_or_create_memory(self, session_id: str) -> List[Dict[str, Any]]:
        """Get or create memory for a session"""
        if session_id not in self.session_memories:
            self.session_memories[session_id] = []
            logger.info(f"Created new memory for session: {session_id}")
        return self.session_memories[session_id]

    def _decode_image(self, base64_data: str) -> Optional[Image.Image]:
        """Decode base64 image data"""
        try:
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]

            image_bytes = base64.b64decode(base64_data)
            image = Image.open(io.BytesIO(image_bytes))

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

        if width > height:
            new_width = max_size
            new_height = int(height * max_size / width)
        else:
            new_height = max_size
            new_width = int(width * max_size / height)

        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def _build_conversation_context(self, session_id: str, current_text: str) -> List[str]:
        """Build conversation context from memory"""
        memory = self._get_or_create_memory(session_id)

        # Format system prompt with available tools
        tools_list = ", ".join(self.available_tools) if self.available_tools else "No tools available"
        formatted_system_prompt = self.config.system_prompt.replace("{tools}", tools_list)
        context_parts = [formatted_system_prompt]

        # Add recent conversation history
        recent_memory = memory[-10:] if len(memory) > 10 else memory
        for entry in recent_memory:
            if entry["type"] == "user":
                context_parts.append(f"User: {entry['content']}")
            elif entry["type"] == "assistant":
                context_parts.append(f"Assistant: {entry['content']}")

        # Add current user input
        context_parts.append(f"User: {current_text}")

        return context_parts

    def _prepare_conversation_context_string(self, session_id: str) -> str:
        """Prepare conversation context as a string for enhanced tool calling"""
        memory = self._get_or_create_memory(session_id)

        context_parts = []
        recent_memory = memory[-5:] if len(memory) > 5 else memory

        for entry in recent_memory:
            if entry["type"] == "user":
                context_parts.append(f"User: {entry['content']}")
            elif entry["type"] == "assistant":
                context_parts.append(f"Assistant: {entry['content']}")

        return "\n".join(context_parts)

    async def _analyze_screen_image(self, image: Image.Image) -> str:
        """Analyze screen image using Gemini to extract meaningful context"""
        if not self.model:
            return "Screen context available but AI service not initialized"

        try:
            # Prepare image analysis prompt
            analysis_prompt = """Analyze this screen image and provide a concise description of what you see based on the user query. Focus on:
1. Main UI elements, text, and content visible
2. Application or website being used
3. Key information that might be relevant for user assistance
4. Any error messages, notifications, or important status indicators

Just describe what is on the screen without giving extra details asked by the user. For example:

Provide a clear, structured description in 2-3 sentences that captures the essential context."""

            # Generate analysis using Gemini
            content = [analysis_prompt, image]
            response = await asyncio.get_event_loop().run_in_executor(None, lambda: self.model.generate_content(content))

            screen_analysis = response.text.strip()
            logger.info(f"Screen analysis completed: {screen_analysis[:100]}...")
            return screen_analysis

        except Exception as e:
            logger.error(f"Error analyzing screen image: {e}")
            return "Screen context available but analysis failed"

    async def _handle_enhanced_tool_calling(self, user_query: str, conversation_context: str, screen_context: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Handle enhanced tool calling if needed"""
        if not self.enhanced_tool_service:
            return None

        try:
            start_time = time.time()

            # Process query with enhanced tool calling (with timeout protection)
            logger.info(f"Starting enhanced tool calling for query: {user_query}")
            result = await asyncio.wait_for(
                self.enhanced_tool_service.process_query(
                    user_query=user_query, conversation_context=conversation_context, screen_context=screen_context, session_id=session_id, available_tools=self.available_tools
                ),
                timeout=45.0,  # 45 second timeout to allow for DSPy processing + tool execution
            )
            logger.info(f"Enhanced tool calling completed in {time.time() - start_time:.2f}s")

            processing_time = time.time() - start_time

            # Update performance metrics
            self.performance_metrics["total_requests"] += 1

            if result["intent_classification"].get("needs_tool", False):
                self.performance_metrics["tool_requests"] += 1

                if result["execution_success"]:
                    self.performance_metrics["successful_tool_calls"] += 1

                # Update average quality score
                quality_score = result["quality_score"]
                current_avg = self.performance_metrics["average_quality_score"]
                tool_requests = self.performance_metrics["tool_requests"]
                self.performance_metrics["average_quality_score"] = (current_avg * (tool_requests - 1) + quality_score) / tool_requests

            # Update average response time
            total_requests = self.performance_metrics["total_requests"]
            current_avg_time = self.performance_metrics["average_response_time"]
            self.performance_metrics["average_response_time"] = (current_avg_time * (total_requests - 1) + processing_time) / total_requests

            # Check if response meets quality threshold
            if result["intent_classification"].get("needs_tool", False) and result["execution_success"] and result["quality_score"] >= self.config.quality_score_threshold:

                logger.info(f"Enhanced tool calling successful with quality score: {result['quality_score']}")
                return result

            elif result["intent_classification"].get("needs_tool", False):
                logger.warning(f"Tool calling attempted but quality too low: {result['quality_score']}")
                return None

            else:
                # No tool needed, return None to use standard LLM response
                return None

        except asyncio.TimeoutError:
            logger.error(f"Enhanced tool calling timed out after 45 seconds for query: {user_query}")
            logger.warning("Tool calling took too long - consider using more specific queries")
            return None
        except Exception as e:
            logger.error(f"Error in enhanced tool calling: {e}")
            import traceback

            traceback.print_exc()
            return None

    async def process_conversation(self, input_data: ConversationInput) -> ConversationResponse:
        """Process a conversation with enhanced tool calling capabilities"""
        start_time = time.time()

        try:
            logger.info(f"Processing enhanced conversation for session {input_data.session_id}")

            if not self.model:
                return ConversationResponse(
                    text="Sorry, the AI service is not available. Please check the API configuration.",
                    timestamp=input_data.timestamp,
                    processing_time=time.time() - start_time,
                    session_id=input_data.session_id,
                )

            # Initialize enhanced tools if not already done
            if not self.enhanced_tool_service and self.config.enable_enhanced_tool_calling:
                await self._initialize_enhanced_tools()

            # Prepare context
            conversation_context = self._prepare_conversation_context_string(input_data.session_id)
            content = ["\n".join(conversation_context)]
            screen_context = ""

            # Handle screen image if provided
            screen_context_data = None
            image = None
            screen_analysis = ""

            if input_data.screen_image:
                image = self._decode_image(input_data.screen_image)
                if image:
                    image = self._resize_image(image)
                    # Analyze the screen image first
                    screen_analysis = await self._analyze_screen_image(image)
                    screen_context = f"Screen analysis: {screen_analysis}"

                    screen_context_data = {"has_screen_context": True, "image_size": image.size, "capture_method": "provided", "analysis": screen_analysis}

                    content.append(image)
                    content[0] += "\n\nScreen sharing is ENABLED. I can see your screen and will provide contextual assistance."
                else:
                    content[0] += "\n\nScreen sharing is currently OFF/DISABLED. I cannot see the user's screen. Do not make up or hallucinate screen content."
            else:
                content[0] += "\n\nScreen sharing is currently OFF/DISABLED. I cannot see the user's screen. Do not make up or hallucinate screen content."

            logger.info(f"Processing conversation for session {input_data.session_id}")

            if input_data.screen_image:
                logger.info("Screen context provided in request")

            # Try enhanced tool calling first
            enhanced_result = None
            if self.config.enable_enhanced_tool_calling:
                # Prepare enhanced query with screen analysis if available
                enhanced_query = input_data.text
                if screen_analysis:
                    enhanced_query = f"{input_data.text}\n\nScreen Context: {screen_analysis}"

                screen_ctx = screen_analysis if screen_analysis else "No screen context available"
                enhanced_result = await self._handle_enhanced_tool_calling(
                    user_query=enhanced_query, conversation_context=conversation_context, screen_context=screen_ctx, session_id=input_data.session_id
                )

            # Use enhanced result if available and high quality
            if enhanced_result and enhanced_result.get("response"):
                response_text = enhanced_result["response"]

                # Add enhancement metadata
                if enhanced_result.get("intent_classification", {}).get("needs_tool", False):
                    tool_name = enhanced_result.get("tool_selection", {}).get("selected_tool", "unknown")
                    quality_score = enhanced_result.get("quality_score", 0.0)

                    logger.info(f"Using enhanced tool calling response: {response_text}")
                    logger.info(f"Tool used: {tool_name}")
                    logger.info(f"Quality score: {quality_score}")

            else:
                # Fall back to standard multimodal response
                logger.info("Using standard LLM response")

                context_parts = self._build_conversation_context(input_data.session_id, input_data.text)
                fallback_content = ["\n".join(context_parts)]

                if input_data.screen_image and image:
                    fallback_content.append(image)
                    fallback_content[0] += "\n\nScreen sharing is ENABLED. I can see your screen and will provide contextual assistance."
                else:
                    fallback_content[0] += "\n\nScreen sharing is currently OFF/DISABLED."

                # Generate response using Gemini
                if self.model:
                    response = await asyncio.get_event_loop().run_in_executor(None, lambda: self.model.generate_content(fallback_content))
                    response_text = response.text
                else:
                    response_text = "Sorry, the AI service is not available."

            # Ensure response_text is valid
            if not isinstance(response_text, str) or not response_text:
                response_text = "I apologize, but I couldn't generate a response."

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
                    "enhanced_tool_used": enhanced_result is not None,
                    "quality_score": enhanced_result.get("quality_score", 0.0) if enhanced_result else 0.0,
                }
            )

            # Keep memory manageable
            if len(memory) > 50:
                memory[:] = memory[-50:]

            processing_time = time.time() - start_time

            logger.info(f"Generated enhanced response in {processing_time:.2f}s")

            return ConversationResponse(
                text=response_text,
                timestamp=input_data.timestamp,
                processing_time=processing_time,
                session_id=input_data.session_id,
                token_count=len(response_text.split()),
                screen_context=screen_context_data,
            )

        except Exception as e:
            logger.error(f"Error processing enhanced conversation: {e}")

            return ConversationResponse(
                text="I apologize, but I encountered an error processing your request. Please try again.",
                timestamp=input_data.timestamp,
                processing_time=time.time() - start_time,
                session_id=input_data.session_id,
            )

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the enhanced service"""
        return {
            **self.performance_metrics,
            "success_rate": (self.performance_metrics["successful_tool_calls"] / max(self.performance_metrics["tool_requests"], 1)),
            "tool_usage_rate": (self.performance_metrics["tool_requests"] / max(self.performance_metrics["total_requests"], 1)),
        }

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

        recent_exchanges = len([m for m in memory[-10:] if m["type"] == "user"])
        enhanced_responses = len([m for m in memory if m.get("enhanced_tool_used", False)])

        return f"Recent conversation with {recent_exchanges} user messages, {enhanced_responses} enhanced responses"

    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        return list(self.session_memories.keys())

    def clear_screen_cache(self):
        """Clear screen analysis cache"""
        self.screen_cache.clear()
        logger.info("Screen cache cleared")


# Factory function
async def create_enhanced_multimodal_service(api_key: str, model_name: str = "gemini-2.0-flash-exp", enable_enhanced_tool_calling: bool = True) -> EnhancedMultimodalService:
    """Create and initialize enhanced multimodal service"""

    config = EnhancedMultimodalConfig(
        model_name=model_name,
        api_key=api_key,
        enable_enhanced_tool_calling=enable_enhanced_tool_calling,
    )

    service = EnhancedMultimodalService(config)

    # Test the connection
    try:
        test_input = ConversationInput(
            text="Hello, this is a connection test for the enhanced system.",
            timestamp=time.time(),
            session_id="test_session",
        )

        response = await service.process_conversation(test_input)
        if response.text and "error" not in response.text.lower():
            logger.info("Enhanced multimodal service initialized successfully")
            service.clear_session_memory("test_session")
        else:
            logger.warning("Enhanced multimodal service test returned error response")

    except Exception as e:
        logger.error(f"Failed to initialize enhanced multimodal service: {e}")
        raise

    return service
