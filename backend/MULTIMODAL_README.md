# Multimodal Service (AI Brain)

## Overview

The Multimodal Service is the "brain" of our AI assistant. It combines transcribed audio, conversation history, and context to generate intelligent, conversational responses using Google's Gemini AI and LangChain memory management.

## Architecture

```
Transcribed Text → 
Screen Context  → Multimodal Service → AI Response → TTS Service
Chat History   →        ↓
                  Gemini + LangChain
                     Memory
```

## Features

- **Gemini AI Integration**: Uses `gemini-1.5-flash` for fast, intelligent responses
- **Smart Memory**: LangChain `ConversationSummaryBufferMemory` for efficient conversation tracking
- **Session Management**: Multiple concurrent conversations with separate memory
- **Context Awareness**: Incorporates screen information and timing context
- **Conversational Style**: Friendly, helpful responses that reference conversation history

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

### Basic Conversation

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
        "screen_info": "Python file open"
    }
)

# Get AI response
response = await service.process_conversation(input_data)
print(f"AI: {response.text}")
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
    model_name: str = "gemini-1.5-flash"          # Gemini model
    api_key: Optional[str] = None                 # API key
    max_tokens: int = 1000                        # Response length limit
    temperature: float = 0.7                      # Creativity (0-1)
    memory_max_token_limit: int = 2000            # Memory size limit
    memory_return_messages: bool = True           # Include full messages
    system_prompt: str = "..."                    # AI personality
```

### Model Options

**Fast Response (Default)**:
```python
config = MultimodalConfig(
    model_name="gemini-1.5-flash",
    temperature=0.7,
    max_tokens=500
)
```

**High Quality Responses**:
```python
config = MultimodalConfig(
    model_name="gemini-1.5-pro",
    temperature=0.5,
    max_tokens=1500
)
```

**Experimental Features**:
```python
config = MultimodalConfig(
    model_name="gemini-2.0-flash-exp",
    temperature=0.8,
    max_tokens=1000
)
```

## Memory Management

### How Memory Works

The service uses LangChain's `ConversationSummaryBufferMemory`:

1. **Recent Messages**: Keeps last ~10 messages in full detail
2. **Summary Buffer**: Summarizes older conversations to save space
3. **Token Limit**: Automatically manages memory size to stay under limits

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

# Get all active sessions
active_sessions = service.get_active_sessions()
```

## Context Integration

The service can use various types of context:

### Screen Context (Future Feature)
```python
context = {
    "screen_info": "Browser with GitHub repository open",
    "app_info": "Chrome",
    "url": "https://github.com/user/project"
}
```

### Timing Context
```python
context = {
    "time_info": "2024-01-15 14:30:00",
    "session_duration": "15 minutes"
}
```

### User Context
```python
context = {
    "user_preferences": "prefers Python over JavaScript",
    "skill_level": "beginner",
    "current_task": "building a web scraper"
}
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
✅ Multimodal Service created successfully

👤 User: Hello! I'm testing the AI assistant.
🤔 AI thinking...
🤖 AI: Hello! It's great to meet you. I'm here to help as your AI assistant...
⏱️  Processing time: 1.23s
📊 Token count: 25

🎯 Key Features Verified:
  ✅ Gemini API integration
  ✅ Conversation memory with LangChain
  ✅ Session management
  ✅ Context handling
  ✅ Error handling
```

## Integration with WebSocket

The service integrates seamlessly with the WebSocket flow:

```python
# In main.py
async def process_with_multimodal_llm(websocket: WebSocket, text: str, timestamp: float):
    multimodal_service = service_manager.get_multimodal_service()
    
    conversation_input = ConversationInput(
        text=text,
        session_id=f"ws_{id(websocket)}",  # WebSocket-based sessions
        timestamp=timestamp,
        context={
            "time_info": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "app_info": "Background Multimodal Assistant"
        }
    )
    
    ai_response = await multimodal_service.process_conversation(conversation_input)
    
    # Send response back to frontend
    await websocket.send_text(json.dumps({
        "type": "ai_response",
        "text": ai_response.text,
        "processing_time": ai_response.processing_time
    }))
```

## System Prompt

The AI is configured with a conversational personality:

```
You are a helpful AI assistant with access to the user's screen and conversation history. 
You can see what they're working on and provide contextual assistance.

Guidelines:
- Be conversational and friendly
- Reference previous parts of the conversation when relevant
- If you notice patterns in what they're asking, point them out helpfully
- Keep responses concise but informative
- Ask clarifying questions when needed
```

## Performance Notes

- **Response Time**: 1-3 seconds for typical responses
- **Memory Efficiency**: Automatically summarizes long conversations
- **Concurrent Sessions**: Supports multiple users simultaneously
- **Error Recovery**: Graceful degradation when API is unavailable

## Troubleshooting

### Common Issues

1. **API Key errors**: Check your Gemini API key is valid
2. **Timeout errors**: Gemini may be under high load
3. **Memory issues**: Long conversations are automatically summarized
4. **Empty responses**: Check internet connection and API status

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
2. STT Service → "Can you help me debug this Python code?"
3. Multimodal Service → Gets text + conversation history + context
4. Gemini AI → "I'd be happy to help debug your Python code! Can you share what specific error you're encountering?"
5. TTS Service → Converts response to speech
6. User hears response
```

## Next Steps

1. ✅ **STT Service** - Complete
2. ✅ **Multimodal Service** - Complete  
3. 🔄 **TTS Service** - Next to implement
4. ⏳ **Screen Context** - Add visual understanding

The conversation brain is now fully functional and ready to provide intelligent responses! 