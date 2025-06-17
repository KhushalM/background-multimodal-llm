#!/usr/bin/env python3
"""
Test script for STT service
"""
import asyncio
import os
import sys
import numpy as np
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.STT import create_stt_service, AudioChunk

# Load environment variables
load_dotenv(override=True)


async def test_stt_service():
    """Test the STT service with synthetic audio"""

    print("🎤 Testing STT Service...")

    try:
        # Create STT service (no token needed for local pipeline)
        async with await create_stt_service() as stt_service:
            print("✅ STT Service created successfully")

        # Generate synthetic audio (sine wave - represents speech)
        sample_rate = 16000
        duration = 3.0  # 3 seconds
        frequency = 440  # A4 note

        t = np.linspace(0, duration, int(sample_rate * duration))
        audio_data = 0.3 * np.sin(2 * np.pi * frequency * t)  # Quiet sine wave

        # Add some random noise to make it more realistic
        noise = 0.05 * np.random.normal(0, 1, len(audio_data))
        audio_data += noise

        print(f"🎵 Generated {duration}s synthetic audio with {len(audio_data)} samples")

        # Create audio chunk
        chunk = AudioChunk(
            data=audio_data.tolist(),
            sample_rate=sample_rate,
            timestamp=asyncio.get_event_loop().time(),
            chunk_id="test_chunk_1",
        )

        print("🔄 Sending audio to STT service...")

        # Transcribe
        result = await stt_service.transcribe_chunk(chunk)

        print(f"📝 Transcription result:")
        print(f"   Text: '{result.text}'")
        print(f"   Processing time: {result.processing_time:.2f}s")
        print(f"   Timestamp: {result.timestamp}")

        if result.text:
            print("✅ STT service is working!")
        else:
            print("⚠️  No transcription returned (expected for synthetic audio)")
            print("   This is normal - try with real speech audio")

        # Test buffer functionality
        print("\n🔄 Testing audio buffer...")

        # Simulate streaming audio in small chunks
        chunk_size = sample_rate // 10  # 0.1 second chunks
        transcriptions = []

        for i in range(0, len(audio_data), chunk_size):
            chunk_data = audio_data[i : i + chunk_size]

            # Add to buffer
            audio_chunk = stt_service.add_audio_to_buffer(chunk_data.tolist(), sample_rate)

            if audio_chunk:
                print(f"📦 Buffer returned chunk after {i/sample_rate:.1f}s")
                result = await stt_service.transcribe_chunk(audio_chunk)
                if result.text:
                    transcriptions.append(result.text)

        # Flush any remaining audio
        final_chunk = stt_service.flush_buffer()
        if final_chunk:
            print("📦 Flushing final buffer")
            result = await stt_service.transcribe_chunk(final_chunk)
            if result.text:
                transcriptions.append(result.text)

        print(f"📊 Total transcriptions from streaming: {len(transcriptions)}")
        for i, text in enumerate(transcriptions):
            print(f"   {i+1}: '{text}'")

        print("\n✅ STT service test completed successfully!")

    except Exception as e:
        print(f"❌ Error testing STT service: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_stt_service())
