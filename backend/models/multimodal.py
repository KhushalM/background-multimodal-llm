import os
import time
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pydantic import BaseModel

import google.generativeai as genai
from langchain.memory import ConversationSummaryBufferMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

@dataclass
class MultimodalConfig:
    """Configuration for Multimodal service"""
    model_name: str = "gemini-1.5-flash"
    api_key: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.7
    memory_max_token_limit: int = 2000
    memory_return_messages: bool = True
    system_prompt: str = """You are a helpful AI assistant with access to the user's screen and conversation history. 
You can see what they're working on and provide contextual assistance.

Guidelines:
- Be conversational and friendly
- Reference previous parts of the conversation when relevant
- If you notice patterns in what they're asking, point them out helpfully
- Keep responses concise but informative
- Ask clarifying questions when needed
"""

class ConversationInput(BaseModel):
    """Input for conversation processing"""
    text: str
    user_id: str = "default"
    session_id: str = "default"
    timestamp: float
    context: Optional[Dict[str, Any]] = None

class ConversationResponse(BaseModel):
    """Response from conversation processing"""
    text: str
    timestamp: float
    processing_time: float
    session_id: str
    token_count: Optional[int] = None

class MultimodalService:
    """Main multimodal service using Gemini + LangChain memory"""
    
    def __init__(self, config: MultimodalConfig):
        self.config = config
        
        # Initialize Gemini
        if config.api_key:
            genai.configure(api_key=config.api_key)
            self.llm = ChatGoogleGenerativeAI(
                model=config.model_name,
                google_api_key=config.api_key,
                temperature=config.temperature,
                max_tokens=config.max_tokens
            )
        else:
            self.llm = None
            logger.warning("No Gemini API key provided")
        
        # Initialize memory for different sessions
        self.session_memories: Dict[str, ConversationSummaryBufferMemory] = {}
        
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
    
    async def process_conversation(self, input_data: ConversationInput) -> ConversationResponse:
        """Process a conversation turn"""
        start_time = time.time()
        
        try:
            if not self.llm:
                return ConversationResponse(
                    text="Sorry, the AI service is not available right now. Please check the API configuration.",
                    timestamp=input_data.timestamp,
                    processing_time=time.time() - start_time,
                    session_id=input_data.session_id
                )
            
            # Get memory for this session
            memory = self._get_or_create_memory(input_data.session_id)
            
            # Get conversation history
            history = memory.chat_memory.messages
            
            # Build the prompt
            prompt_input = {
                "history": history,
                "input": input_data.text
            }
            
            # Add context if available
            if input_data.context:
                context_str = self._format_context(input_data.context)
                prompt_input["input"] = f"Context: {context_str}\n\nUser: {input_data.text}"
            
            logger.info(f"Processing conversation for session {input_data.session_id}")
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
            
            return ConversationResponse(
                text=response_text,
                timestamp=input_data.timestamp,
                processing_time=processing_time,
                session_id=input_data.session_id,
                token_count=len(response_text.split())  # Simple token estimate
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

# Factory function
async def create_multimodal_service(api_key: str, model_name: str = "gemini-1.5-flash") -> MultimodalService:
    """Create and initialize multimodal service"""
    config = MultimodalConfig(
        model_name=model_name,
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
            logger.info("Multimodal service initialized successfully")
            # Clean up test session
            service.clear_session_memory("test_session")
        else:
            logger.warning("Multimodal service test returned error response")
            
    except Exception as e:
        logger.error(f"Failed to initialize multimodal service: {e}")
        raise
    
    return service
