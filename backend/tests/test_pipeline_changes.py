#!/usr/bin/env python3
"""
Quick test script to verify STT and TTS pipeline changes work
"""
import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.STT import create_stt_service, AudioChunk
from models.TTS import create_tts_service, TTSRequest
from models.multimodal import create_multimodal_service, ConversationInput

# Load environment variables
load_dotenv(override=True)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_pipeline_changes():
    """Test that the new pipeline-based approach works"""

    print("🧪 Testing Pipeline Changes...")
    print("=" * 50)

    # Test STT Service
    print("\n🎤 Testing STT Service (Local Pipeline)...")
    try:
        async with await create_stt_service() as stt_service:
            print("✅ STT service initialized successfully")

            # Create a dummy audio chunk for testing
            import numpy as np

            sample_rate = 16000
            duration = 1.0
            t = np.linspace(0, duration, int(sample_rate * duration))
            audio_data = 0.1 * np.sin(2 * np.pi * 440 * t)  # Simple sine wave

            chunk = AudioChunk(
                data=audio_data.tolist(),
                sample_rate=sample_rate,
                timestamp=asyncio.get_event_loop().time(),
                chunk_id="test_chunk",
            )

            result = await stt_service.transcribe_chunk(chunk)
            print(
                f"📝 STT Test Result: '{result.text}' (processing time: {result.processing_time:.2f}s)"
            )
            print("✅ STT service working (no transcription expected for sine wave)")

    except Exception as e:
        print(f"❌ STT service failed: {e}")
        return False

    # Test TTS Service
    print("\n🗣️ Testing TTS Service (Local Pipeline)...")
    try:
        async with await create_tts_service() as tts_service:
            print("✅ TTS service initialized successfully")

            request = TTSRequest(
                text="Hello! This is a test of the new pipeline approach.",
                voice_preset="default",
                session_id="test_session",
            )

            response = await tts_service.synthesize_speech(request)
            print(
                f"🔊 TTS Test Result: {response.duration:.2f}s audio generated in {response.processing_time:.2f}s"
            )
            print(f"📊 Audio samples: {len(response.audio_data)}")
            print("✅ TTS service working")

    except Exception as e:
        print(f"❌ TTS service failed: {e}")
        return False

    # Test Multimodal Service (should still work with API)
    print("\n🧠 Testing Multimodal Service...")
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            multimodal_service = await create_multimodal_service(gemini_key)
            print("✅ Multimodal service initialized successfully")

            conversation_input = ConversationInput(
                text="Hello, how are you?",
                session_id="test_session",
                timestamp=asyncio.get_event_loop().time(),
            )

            response = await multimodal_service.process_conversation(conversation_input)
            print(f"🤖 Multimodal Response: '{response.text[:100]}...'")
            print("✅ Multimodal service working")

        except Exception as e:
            print(f"❌ Multimodal service failed: {e}")
            return False
    else:
        print("⚠️ No Gemini API key found, skipping multimodal test")

    print("\n🎉 All pipeline changes working successfully!")
    print("\n📋 Summary of Changes:")
    print("  • STT now uses local Transformers pipeline (no HF token needed)")
    print("  • TTS now uses local Transformers pipeline (no HF token needed)")
    print("  • Multimodal still uses Gemini API (Gemini key still needed)")
    print("  • Better performance and reliability with local models")
    print("  • Reduced API dependency")

    return True


if __name__ == "__main__":
    asyncio.run(test_pipeline_changes())
