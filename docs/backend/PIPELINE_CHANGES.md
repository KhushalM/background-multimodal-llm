# Pipeline Changes: API to Local Transformers

## Overview

We've successfully migrated the STT and TTS services from using HuggingFace Inference API to local Transformers pipelines for better performance, reliability, and reduced API dependency.

## Changes Made

### 1. STT Service (`backend/models/STT.py`)

**Before:** 
- Used HuggingFace Inference API
- Required `HUGGINGFACE_API_TOKEN`
- Network-dependent
- Variable latency due to API calls

**After:**
- Uses local Transformers pipeline
- No API token required
- Runs locally for better performance
- Consistent low latency

**Key Changes:**
- Removed `httpx` dependency for API calls
- Added `transformers` pipeline with `AutoModelForSpeechSeq2Seq`
- Automatic device detection (CUDA/MPS/CPU)
- Local model loading with memory optimization

### 2. TTS Service (`backend/models/TTS.py`)

**Before:**
- Used HuggingFace Inference API  
- Required `HUGGINGFACE_API_TOKEN`
- Network-dependent
- Limited voice control

**After:**
- Uses local Transformers pipeline with SpeechT5
- No API token required
- Local synthesis with HiFiGAN vocoder
- Better voice quality and control

**Key Changes:**
- Removed API calls, added local `SpeechT5ForTextToSpeech`
- Added `SpeechT5HifiGan` vocoder for better audio quality
- Speaker embeddings from CMU Arctic dataset
- Device-aware model loading

### 3. Service Manager (`backend/services/service_manager.py`)

**Changes:**
- Removed dependency on `HUGGINGFACE_API_TOKEN`
- Updated service initialization to use local pipelines
- Only `GEMINI_API_KEY` required now (for multimodal service)

### 4. Test Files

All test files updated to work without HuggingFace tokens:
- `test_stt.py` - Updated for local pipeline testing
- `test_tts.py` - Updated for local pipeline testing  
- `test_pipeline.py` - Updated for integrated testing

## Benefits

### Performance
- **Faster**: No network round-trips
- **Consistent**: No API rate limiting or timeouts
- **Offline**: Works without internet connection

### Reliability
- **No API failures**: Local processing eliminates API downtime
- **Predictable**: Consistent performance regardless of network
- **Robust**: Better error handling and recovery

### Cost & Privacy
- **Reduced costs**: No API usage fees for STT/TTS
- **Privacy**: Audio processing happens locally
- **Independence**: Less dependency on external services

## Requirements

### New Dependencies
Added to `requirements.txt`:
- `accelerate>=0.20.0` - For optimized model loading
- Existing `transformers`, `torch`, `datasets` dependencies

### Hardware Requirements
- **Minimum**: CPU-only (slower but functional)
- **Recommended**: NVIDIA GPU with CUDA or Apple Silicon with MPS
- **Memory**: 4-8GB RAM for models (depends on batch size)

## Model Details

### STT Model: `distil-whisper/distil-large-v3.5`
- **Size**: ~756MB
- **Language**: English (configurable)
- **Performance**: Fast inference, good accuracy
- **Features**: Timestamps, streaming support

### TTS Model: `microsoft/speecht5_tts`
- **Size**: ~133MB + ~200MB vocoder
- **Quality**: High-quality neural synthesis
- **Vocoder**: SpeechT5HifiGan for natural audio
- **Speaker**: CMU Arctic embeddings

## Migration Guide

### For Developers

1. **Remove HF tokens**: No longer needed for STT/TTS
2. **Update service calls**: Services now auto-initialize pipelines
3. **Handle async context**: Use `async with` for proper cleanup
4. **Check device**: Services auto-detect best device (CUDA/MPS/CPU)

### For Deployment

1. **Install dependencies**: Run `pip install -r requirements.txt`
2. **First run**: Models download automatically (~1GB total)
3. **Environment**: Only `GEMINI_API_KEY` required now
4. **Resources**: Ensure adequate RAM/VRAM for models

## Testing

Run the test suite to verify changes:

```bash
# Test individual services
python backend/test_stt.py
python backend/test_tts.py

# Test complete pipeline
python backend/test_pipeline.py

# Quick verification
python backend/test_pipeline_changes.py
```

## Configuration

### Device Selection
```python
# Auto-detect best device
config = STTConfig(device="auto")  # Chooses CUDA > MPS > CPU

# Force specific device
config = STTConfig(device="cuda")   # Force CUDA
config = STTConfig(device="cpu")    # Force CPU only
```

### Memory Optimization
```python
# For low-memory systems
config = STTConfig(torch_dtype="float16")  # Use half precision

# For better quality
config = STTConfig(torch_dtype="float32")  # Use full precision
```

## Troubleshooting

### Common Issues

1. **CUDA out of memory**: Use `device="cpu"` or `torch_dtype="float16"`
2. **Slow first run**: Models are downloading, subsequent runs are fast
3. **Import errors**: Install missing dependencies with `pip install -r requirements.txt`

### Performance Tips

1. **GPU acceleration**: Install PyTorch with CUDA support
2. **Memory management**: Services auto-cleanup with `async with`
3. **Batch processing**: Use batch methods for multiple requests

## Future Enhancements

- [ ] Add more TTS voice options (different speaker embeddings)
- [ ] Support for multilingual STT models
- [ ] Model quantization for smaller memory footprint
- [ ] Streaming TTS for real-time synthesis
- [ ] Voice cloning capabilities

## Conclusion

The migration to local Transformers pipelines provides significant improvements in performance, reliability, and cost-effectiveness while maintaining the same API interface. The system is now more robust and suitable for production deployment. 