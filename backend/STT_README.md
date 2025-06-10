# Speech-to-Text (STT) Service

## Overview

The STT service converts real-time audio streams to text using HuggingFace's Whisper models. It's designed for low-latency transcription in a multimodal AI assistant.

## Features

- **Real-time transcription** using HuggingFace Inference API
- **Audio buffering** for streaming input
- **Automatic resampling** to 16kHz (Whisper requirement)
- **Error handling & retries** for robust operation
- **Configurable chunk sizes** for different latency/accuracy tradeoffs

## Models Supported

- `openai/whisper-large-v3` (default) - Best accuracy
- `openai/whisper-medium` - Good balance
- `openai/whisper-small` - Faster inference
- `distil-whisper/distil-large-v3` - Optimized for speed

## Setup

### 1. Get HuggingFace API Token

1. Go to [HuggingFace](https://huggingface.co/settings/tokens)
2. Create a new token with "Read" access
3. Copy the token

### 2. Environment Setup

```bash
# Copy environment template
cp backend/env.example backend/.env

# Edit .env file and add your token
HUGGINGFACE_API_TOKEN=your_token_here
```

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

## Usage

### Basic Usage

```python
from models.STT import create_stt_service, AudioChunk

# Create service
stt_service = await create_stt_service("your_hf_token")

# Create audio chunk
chunk = AudioChunk(
    data=[0.1, 0.2, 0.3, ...],  # Audio samples as float list
    sample_rate=16000,
    timestamp=time.time()
)

# Transcribe
result = await stt_service.transcribe_chunk(chunk)
print(f"Transcription: {result.text}")
```

### Streaming Usage (Recommended)

```python
# For real-time streaming, use the buffer system
for audio_data in audio_stream:
    # Add audio to buffer
    chunk = stt_service.add_audio_to_buffer(audio_data, sample_rate)
    
    if chunk:  # Buffer is ready for transcription
        result = await stt_service.transcribe_chunk(chunk)
        if result.text:
            print(f"Transcription: {result.text}")

# Don't forget to flush the final buffer
final_chunk = stt_service.flush_buffer()
if final_chunk:
    result = await stt_service.transcribe_chunk(final_chunk)
```

## Configuration

### STTConfig Parameters

```python
@dataclass
class STTConfig:
    model_name: str = "openai/whisper-large-v3"  # HF model to use
    hf_token: Optional[str] = None               # HF API token
    sample_rate: int = 16000                     # Target sample rate
    chunk_duration: float = 2.0                 # Chunk size in seconds
    max_retries: int = 3                         # API retry attempts
    timeout: float = 30.0                       # Request timeout
```

### Optimizing for Your Use Case

**Low Latency (Real-time chat)**:
```python
config = STTConfig(
    model_name="distil-whisper/distil-large-v3",
    chunk_duration=1.0,  # Smaller chunks
    timeout=10.0
)
```

**High Accuracy (Transcription)**:
```python
config = STTConfig(
    model_name="openai/whisper-large-v3",
    chunk_duration=5.0,  # Larger chunks
    timeout=60.0
)
```

## Testing

Run the test script to verify everything works:

```bash
cd backend
python test_stt.py
```

Expected output:
```
🎤 Testing STT Service...
✅ STT Service created successfully
🎵 Generated 3.0s synthetic audio with 48000 samples
🔄 Sending audio to STT service...
📝 Transcription result:
   Text: ''
   Processing time: 2.34s
   Timestamp: 1704123456.789
⚠️  No transcription returned (expected for synthetic audio)
   This is normal - try with real speech audio
✅ STT service test completed successfully!
```

## Integration with WebSocket

The service is integrated into the main WebSocket handler:

```python
# In main.py
async def handle_audio_data(websocket: WebSocket, message: Dict[str, Any]):
    audio_data = message.get("data", [])
    stt_service = service_manager.get_stt_service()
    
    # Process streaming audio
    chunk = stt_service.add_audio_to_buffer(audio_data, 16000)
    if chunk:
        result = await stt_service.transcribe_chunk(chunk)
        if result.text:
            # Send transcription to client
            await websocket.send_text(json.dumps({
                "type": "transcription_result",
                "text": result.text
            }))
```

## Performance Notes

- **First request**: May take 10-30 seconds (model loading)
- **Subsequent requests**: 1-5 seconds depending on audio length
- **Chunk overlap**: 0.5 seconds to maintain context
- **Memory usage**: ~100MB for audio buffers

## Troubleshooting

### Common Issues

1. **"Model loading" errors**: Wait 30 seconds and retry
2. **Authentication errors**: Check your HF token
3. **Timeout errors**: Increase timeout or use smaller chunks
4. **Empty transcriptions**: Normal for non-speech audio

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Next Steps

1. ✅ **STT Service** - Complete
2. 🔄 **Conversation Memory** - Next to implement
3. ⏳ **Multimodal Service** - Pending
4. ⏳ **TTS Service** - Pending

The STT service is now ready to be integrated with the multimodal LLM! 