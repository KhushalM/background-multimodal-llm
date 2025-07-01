# Multimodal Service with Integrated Screen Context (AI Brain)

## Overview

The Multimodal Service is the "brain" of our AI assistant. It combines transcribed audio, conversation history, **screen visual context**, and traditional context to generate intelligent, conversational responses using Google's Gemini AI with vision capabilities and LangChain memory management.

## Architecture

```
Transcribed Text → 
Screen Image    → Multimodal Service → AI Response → TTS Service
Chat History   →        ↓
Traditional    →  Gemini + Vision + LangChain
Context        →        Memory
```

## Features

- **Gemini AI Integration**: Uses `gemini-2.0-flash-exp` for fast, intelligent responses
- **Gemini Vision**: Integrated screen analysis for visual context understanding
- **Smart Memory**: LangChain `ConversationSummaryBufferMemory` for efficient conversation tracking
- **Session Management**: Multiple concurrent conversations with separate memory
- **Screen Context Awareness**: Analyzes screen captures to understand what the user is working on
- **Context Caching**: Intelligent caching of screen analyses to reduce API calls
- **Conversational Style**: Friendly, helpful responses that reference conversation history and screen content

## Setup

### 1. Get Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Copy the key

### 2. Environment Setup

```bash
# Add to backend/.env file
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

## Usage

### Basic Conversation (Text Only)

```python
from models.multimodal import create_multimodal_service, ConversationInput

# Create service
service = await create_multimodal_service("your_api_key")

# Create conversation input
input_data = ConversationInput(
    text="Hello! Can you help me with Python programming?",
    session_id="user_123",
    timestamp=time.time(),
    context={
        "app_info": "VS Code",
        "time_info": "2024-01-15 14:30:00"
    }
)

# Get AI response
response = await service.process_conversation(input_data)
print(f"AI: {response.text}")
```

### Conversation with Screen Context

```python
# Include screen image (base64 encoded)
input_data = ConversationInput(
    text="What's wrong with this code?",
    session_id="user_123",
    timestamp=time.time(),
    context={
        "app_info": "VS Code",
        "time_info": "2024-01-15 14:30:00"
    },
    screen_image="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ..."  # base64 encoded screenshot
)

response = await service.process_conversation(input_data)
print(f"AI: {response.text}")

# The response may include screen context analysis
if response.screen_context:
    print(f"Screen Analysis: {response.screen_context}")
```

### Session Management

```python
# Multiple sessions with separate memory
session1 = "user_alice"
session2 = "user_bob"

# Each session maintains its own conversation history
response1 = await service.process_conversation(
    ConversationInput(text="I'm learning React", session_id=session1, timestamp=time.time())
)

response2 = await service.process_conversation(
    ConversationInput(text="I'm learning Python", session_id=session2, timestamp=time.time())
)

# Get conversation history for each session
alice_history = service.get_conversation_history(session1)
bob_history = service.get_conversation_history(session2)
```

## Configuration

### MultimodalConfig Parameters

```python
@dataclass
class MultimodalConfig:
    model_name: str = "gemini-2.0-flash-exp"         # Gemini model for text
    vision_model: str = "gemini-2.0-flash-exp"       # Gemini model for vision
    api_key: Optional[str] = None                 # API key
    max_tokens: int = 1000                        # Response length limit
    temperature: float = 0.7                      # Creativity (0-1)
    memory_max_token_limit: int = 2000            # Memory size limit
    memory_return_messages: bool = True           # Include full messages
    # Screen context settings
    max_image_size: int = 1024                    # Max image dimensions
    compression_quality: int = 85                 # JPEG compression quality
    analysis_interval: float = 2.0                # Cache interval
    cache_duration: float = 30.0                  # Cache duration
    system_prompt: str = "..."                    # AI personality
```

### Model Options

**Fast Response with Vision (Default)**:
```python
config = MultimodalConfig(
    model_name="gemini-2.0-flash-exp",
    vision_model="gemini-2.0-flash-exp",
    temperature=0.7,
    max_tokens=500
)
```

**High Quality Responses with Vision**:
```python
config = MultimodalConfig(
    model_name="gemini-1.5-pro",
    vision_model="gemini-1.5-pro",
    temperature=0.5,
    max_tokens=1500
)
```

## Screen Context Integration

### How Screen Analysis Works

The service automatically analyzes screen images when provided:

1. **Image Processing**: Resizes and optimizes images for analysis
2. **Vision Analysis**: Uses Gemini Vision to understand screen content
3. **Context Extraction**: Identifies UI elements, content type, and relevant information
4. **Caching**: Stores analysis results to avoid repeated processing
5. **Integration**: Includes screen context in conversation prompts

### Screen Analysis Output

```python
screen_context = {
    "description": "A code editor showing Python code with syntax highlighting",
    "context_type": "code",
    "confidence": 0.95,
    "elements": ["code editor", "Python syntax", "function definition", "error highlight"]
}
```

### Context Types

- **code**: Programming/development environments
- **document**: Text documents, PDFs, etc.
- **browser**: Web pages, online content
- **terminal**: Command line interfaces
- **design**: Design tools, graphics software
- **general**: Other applications

## Memory Management

### How Memory Works

The service uses LangChain's `ConversationSummaryBufferMemory`:

1. **Recent Messages**: Keeps last ~10 messages in full detail
2. **Summary Buffer**: Summarizes older conversations to save space
3. **Token Limit**: Automatically manages memory size to stay under limits
4. **Screen Context**: Recent screen analyses are included in conversation context

### Memory Features

```python
# Get conversation history
history = service.get_conversation_history(session_id)
print(f"Messages in memory: {len(history)}")

# Get conversation summary (for long conversations)
summary = service.get_session_summary(session_id)
if summary:
    print(f"Summary: {summary}")

# Clear session memory
service.clear_session_memory(session_id)

# Clear screen analysis cache
service.clear_screen_cache()

# Get all active sessions
active_sessions = service.get_active_sessions()
```

## Context Integration

The service can use various types of context:

### Screen Context (Integrated)
```python
# Automatically processed when screen_image is provided
input_data = ConversationInput(
    text="Help me fix this error",
    screen_image="base64_encoded_screenshot",
    session_id="user_123",
    timestamp=time.time()
)
```

### Traditional Context
```python
context = {
    "time_info": "2024-01-15 14:30:00",
    "app_info": "VS Code",
    "session_duration": "15 minutes"
}
```

### Combined Context
```python
# Both screen and traditional context
input_data = ConversationInput(
    text="What should I do next?",
    screen_image="base64_screenshot",
    context={
        "time_info": "2024-01-15 14:30:00",
        "app_info": "VS Code",
        "user_skill": "beginner"
    },
    session_id="user_123",
    timestamp=time.time()
)
```

## Testing

Run the test script to verify functionality:

```bash
cd backend
python test_multimodal.py
```

Expected output:
```
🧠 Testing Multimodal Service...
📡 Connecting to Gemini API...
✅ Multimodal Service with screen context initialized successfully

👤 User: Hello! I'm testing the AI assistant.
🤔 AI thinking...
🤖 AI: Hello! It's great to meet you. I'm here to help as your AI assistant...
⏱️  Processing time: 1.23s
📊 Token count: 25
🖥️ Screen context: Available

🎯 Key Features Verified:
  ✅ Gemini AI integration
  ✅ Gemini Vision integration
  ✅ Conversation memory with LangChain
  ✅ Session management
  ✅ Screen context analysis
  ✅ Context caching
  ✅ Error handling
```

## Integration with WebSocket

The service integrates seamlessly with the WebSocket flow:

```python
# In main.py
async def process_with_multimodal_llm(websocket: WebSocket, text: str, timestamp: float, screen_image: str = None):
    multimodal_service = service_manager.get_multimodal_service()
    
    conversation_input = ConversationInput(
        text=text,
        session_id=f"ws_{id(websocket)}",  # WebSocket-based sessions
        timestamp=timestamp,
        context={
            "time_info": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "app_info": "Background Multimodal Assistant"
        },
        screen_image=screen_image  # Optional screen context
    )
    
    ai_response = await multimodal_service.process_conversation(conversation_input)
    
    # Send response back to frontend (including screen context if available)
    response = {
        "type": "ai_response",
        "text": ai_response.text,
        "processing_time": ai_response.processing_time
    }
    
    if ai_response.screen_context:
        response["screen_context"] = ai_response.screen_context
    
    await websocket.send_text(json.dumps(response))
```

## System Prompt

The AI is configured with an enhanced conversational personality:

```
You are a helpful AI assistant with access to the user's screen and conversation history. 
You can see what they're working on and provide contextual assistance.

Guidelines:
- Be conversational and friendly
- Reference previous parts of the conversation when relevant
- If you notice patterns in what they're asking, point them out helpfully
- Keep responses concise but informative
- Ask clarifying questions when needed
- When screen context is available, use it to provide more relevant assistance
- Mention what you can see on their screen when it helps with your response
```

## Performance Notes

- **Response Time**: 1-3 seconds for text responses, 2-5 seconds with screen analysis
- **Memory Efficiency**: Automatically summarizes long conversations
- **Screen Analysis**: Cached for 30 seconds to reduce API calls
- **Concurrent Sessions**: Supports multiple users simultaneously
- **Error Recovery**: Graceful degradation when API is unavailable

## Troubleshooting

### Common Issues

1. **API Key errors**: Check your Gemini API key is valid
2. **Timeout errors**: Gemini may be under high load
3. **Memory issues**: Long conversations are automatically summarized
4. **Empty responses**: Check internet connection and API status
5. **Screen analysis fails**: Check image format and size

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Complete Flow Example

Here's how everything works together:

```
1. User speaks → "Can you help me debug this Python code?"
2. Frontend captures screen → Sends audio + screenshot
3. STT Service → "Can you help me debug this Python code?"
4. Multimodal Service → Gets text + conversation history + screen analysis
5. Gemini Vision → Analyzes screenshot: "Python code with syntax error on line 15"
6. Gemini AI → "I can see you have a Python syntax error on line 15. The issue is..."
7. TTS Service → Converts response to speech
8. User hears contextual response
```

## Next Steps

1. ✅ **STT Service** - Complete
2. ✅ **Multimodal Service with Screen Context** - Complete  
3. ✅ **TTS Service** - Complete
4. ✅ **Integrated Pipeline** - Complete

The conversation brain with visual understanding is now fully functional and ready to provide intelligent, context-aware responses! 