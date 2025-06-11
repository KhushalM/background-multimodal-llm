# Text-to-Speech (TTS) Service

## Overview

The TTS service converts AI assistant responses to natural-sounding speech using HuggingFace's advanced TTS models. It completes the conversation loop by providing audio responses that users can hear.

## Features

- **HuggingFace TTS Integration**: Uses state-of-the-art models like SpeechT5
- **Text Preprocessing**: Cleans and optimizes text for better pronunciation
- **Multiple Voice Presets**: Support for different voice characteristics
- **Audio Post-processing**: Normalizes and optimizes audio output
- **Batch Processing**: Efficient handling of multiple text inputs
- **Error Handling**: Graceful fallbacks and retry logic

## Models Supported

- `microsoft/speecht5_tts` (default) - High quality, good balance
- `espnet/kan-bayashi_ljspeech_vits` - Very high quality
- `facebook/mms-tts-eng` - Multilingual support
- `suno/bark` - Very natural but slower

## Setup

### 1. HuggingFace API Token

Use the same token as for STT service:

```bash
# In backend/.env file
HUGGINGFACE_API_TOKEN=your_hf_token_here
```

### 2. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

## Usage

### Basic Usage

```python
from models.TTS import create_tts_service, TTSRequest

# Create service
tts_service = await create_tts_service("your_hf_token")

# Create request
request = TTSRequest(
    text="Hello! I'm your AI assistant. How can I help you today?",
    voice_preset="default",
    session_id="user_123"
)

# Generate speech
response = await tts_service.synthesize_speech(request)

print(f"Generated {response.duration:.1f}s of audio")
print(f"Audio data: {len(response.audio_data)} samples")
```

### Batch Processing

```python
# Convert multiple responses to speech
texts = [
    "Hello! How can I help you?",
    "I understand your question.",
    "Here's what I recommend."
]

responses = await tts_service.synthesize_batch(texts, "session_123")

for i, response in enumerate(responses):
    print(f"Response {i+1}: {response.duration:.1f}s audio")
```

## Configuration

### TTSConfig Parameters

```python
@dataclass
class TTSConfig:
    model_name: str = "microsoft/speecht5_tts"  # TTS model to use
    hf_token: Optional[str] = None              # HF API token
    voice_preset: str = "default"               # Default voice
    sample_rate: int = 16000                    # Audio sample rate
    max_retries: int = 3                        # API retry attempts
    timeout: float = 30.0                       # Request timeout
```

### Model Optimization

**Fast Generation (Real-time)**:
```python
config = TTSConfig(
    model_name="microsoft/speecht5_tts",
    timeout=15.0
)
```

**High Quality (Better audio)**:
```python
config = TTSConfig(
    model_name="espnet/kan-bayashi_ljspeech_vits",
    timeout=45.0
)
```

**Multilingual Support**:
```python
config = TTSConfig(
    model_name="facebook/mms-tts-eng",
    timeout=30.0
)
```

## Text Preprocessing

The service automatically cleans text for better speech synthesis:

### Character Replacements
```python
replacements = {
    "&": "and",
    "@": "at", 
    "#": "hashtag",
    "$": "dollar",
    "%": "percent",
    "...": ". ",
    "—": " - "
}
```

### Length Limits
- Long texts (>500 chars) are automatically truncated
- Split into sentences for better processing
- Maintains natural speech flow

## Voice Presets

Available voice options:
- `"default"` - Standard neutral voice
- `"male"` - Male voice characteristics
- `"female"` - Female voice characteristics  
- `"neutral"` - Gender-neutral voice

```python
request = TTSRequest(
    text="Hello there!",
    voice_preset="female"  # Use female voice
)
```

## Audio Processing

### Output Format
- **Sample Rate**: 16kHz (matches STT input)
- **Format**: Float32 audio samples
- **Channels**: Mono
- **Normalization**: Automatic level adjustment

### Quality Metrics
```python
response = await tts_service.synthesize_speech(request)

print(f"Duration: {response.duration:.2f}s")
print(f"Processing time: {response.processing_time:.2f}s") 
print(f"Efficiency: {response.duration/response.processing_time:.1f}x real-time")
print(f"Sample rate: {response.sample_rate}Hz")
```

## Testing

Run the comprehensive test suite:

```bash
cd backend
python test_tts.py
```

Expected output:
```
🗣️ Testing TTS Service...
📡 Connecting to HuggingFace TTS API...
✅ TTS Service created successfully

🎯 Test 1: Simple greeting
📝 Text: "Hello! Welcome to the AI assistant."
🔄 Generating speech...
✅ Generated audio:
   Duration: 2.34s
   Processing time: 3.21s
   Efficiency: 0.7x real-time
   Audio levels: ✅ Audio levels look good

🎯 Key Features Verified:
  ✅ HuggingFace TTS API integration
  ✅ Text preprocessing and cleaning
  ✅ Audio generation and post-processing
  ✅ Multiple voice presets
  ✅ Batch processing
```

## Integration with WebSocket

The TTS service integrates seamlessly with the conversation flow:

```python
# In main.py - after AI generates response
async def process_with_tts(websocket: WebSocket, text: str, session_id: str):
    tts_service = service_manager.get_tts_service()
    
    tts_request = TTSRequest(
        text=text,
        voice_preset="default", 
        session_id=session_id
    )
    
    tts_response = await tts_service.synthesize_speech(tts_request)
    
    # Send audio back to frontend
    await websocket.send_text(json.dumps({
        "type": "audio_response",
        "audio_data": tts_response.audio_data,
        "sample_rate": tts_response.sample_rate,
        "duration": tts_response.duration
    }))
```

## Complete Pipeline Flow

Here's the full conversation cycle:

```
1. 🎤 User speaks → STT Service → "Help me with Python"
2. 🧠 Multimodal Service → "I'd be happy to help with Python! What do you need?"
3. 🗣️ TTS Service → Converts text to audio samples
4. 📱 WebSocket → Sends audio to frontend
5. 🔊 Frontend → Plays audio response to user
```

## Performance Optimization

### Latency Considerations
- **Model loading**: First request takes 10-30s
- **Subsequent requests**: 2-8s depending on text length
- **Real-time factor**: 0.5-2x (varies by model and text)

### Memory Usage
- **Service**: ~50MB base memory
- **Per request**: ~10-50MB depending on text length
- **Audio buffer**: ~1MB per minute of audio

### Tips for Better Performance
1. **Keep text concise** - Shorter texts process faster
2. **Use default voice** - Custom voices may be slower
3. **Batch related texts** - More efficient than individual requests
4. **Cache common responses** - Store frequent AI responses

## Error Handling

The service includes robust error handling:

### Common Scenarios
```python
# API timeout
if response.audio_format == "silence":
    print("TTS service returned silence - API issue")

# Empty response  
if len(response.audio_data) == 0:
    print("No audio generated - check text input")

# Network issues
except httpx.TimeoutException:
    print("Request timeout - try again or use shorter text")
```

### Fallback Behavior
- Returns 1 second of silence on API failure
- Automatic retries with exponential backoff
- Graceful degradation when service unavailable

## WebSocket Integration Example

Frontend can play the audio like this:

```javascript
// Handle audio response from WebSocket
websocket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === "audio_response") {
        // Convert float array to audio buffer
        const audioData = new Float32Array(data.audio_data);
        const audioBuffer = audioContext.createBuffer(
            1, // mono
            audioData.length,
            data.sample_rate
        );
        
        audioBuffer.getChannelData(0).set(audioData);
        
        // Play the audio
        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext.destination);
        source.start();
    }
};
```

## Next Steps

1. ✅ **STT Service** - Complete
2. ✅ **Multimodal Service** - Complete  
3. ✅ **TTS Service** - Complete
4. 🔄 **Screen Context** - Add visual understanding
5. ⏳ **Frontend Audio** - Update UI to play TTS responses

The full conversation pipeline is now complete! Users can:
- 🎤 **Speak** → AI hears and transcribes
- 🧠 **Think** → AI understands and responds  
- 🗣️ **Reply** → AI converts response to speech
- 🔊 **Listen** → User hears the AI response

This creates a natural, voice-driven conversation experience! 🎉 