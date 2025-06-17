#!/usr/bin/env python3
"""
Test script for speech session-based STT processing
"""
import asyncio
import numpy as np
import os
import sys
import time
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.STT import create_stt_service

# Load environment variables
load_dotenv(override=True)


async def test_speech_sessions():
    """Test the new speech session-based processing"""

    print("🎤 Testing Speech Session-Based STT Processing...")
    print("=" * 60)

    try:
        async with await create_stt_service() as stt_service:
            print("✅ STT service initialized successfully")

            # Simulate a realistic speech scenario
            sample_rate = 16000

            # Generate synthetic speech audio (3 seconds)
            print("\n🎵 Generating synthetic speech audio...")
            speech_duration = 3.0
            t = np.linspace(0, speech_duration, int(sample_rate * speech_duration))

            # Create speech-like audio with varying frequencies
            speech_audio = (
                0.3 * np.sin(2 * np.pi * 200 * t)  # Low frequency
                + 0.2 * np.sin(2 * np.pi * 800 * t)  # Mid frequency
                + 0.1 * np.sin(2 * np.pi * 1600 * t)  # High frequency
            )

            # Add speech envelope
            envelope = np.exp(-t / 3) * (1 + 0.5 * np.sin(2 * np.pi * 2 * t))
            speech_audio *= envelope

            # Add some noise
            noise = 0.05 * np.random.normal(0, 1, len(speech_audio))
            speech_audio += noise

            print(f"Generated {speech_duration}s of synthetic speech")

            # Test 1: Simulate continuous speech session
            print("\n📡 Test 1: Continuous Speech Session")
            print("-" * 40)

            chunk_size = sample_rate // 10  # 0.1 second chunks
            transcriptions = []

            # Send speech chunks with VAD indicating speech is active
            for i in range(0, len(speech_audio), chunk_size):
                chunk_data = speech_audio[i : i + chunk_size]
                timestamp = time.time() + (i / sample_rate)

                # VAD indicates speech is active
                vad_info = {"isSpeaking": True, "energy": 0.1, "confidence": 0.8}

                audio_chunk = stt_service.process_audio_with_vad(
                    chunk_data.tolist(), sample_rate, vad_info, timestamp
                )

                if audio_chunk:
                    print(
                        f"⚠️  Unexpected chunk returned during speech at {i/sample_rate:.1f}s"
                    )
                    result = await stt_service.transcribe_chunk(audio_chunk)
                    transcriptions.append(result.text)

            # End speech session by sending silence
            print("🔇 Ending speech session...")
            silence_vad = {"isSpeaking": False, "energy": 0.001, "confidence": 0.1}

            final_chunk = stt_service.process_audio_with_vad(
                [0.0] * 1000, sample_rate, silence_vad, time.time()
            )

            if final_chunk:
                print(
                    f"✅ Speech session completed with {final_chunk.data.__len__()/sample_rate:.2f}s of audio"
                )
                result = await stt_service.transcribe_chunk(final_chunk)
                transcriptions.append(result.text)
                print(f"📝 Final transcription: '{result.text}'")
            else:
                print("❌ No final chunk returned")

            print(f"\n📊 Test 1 Results:")
            print(f"   Total transcriptions: {len(transcriptions)}")
            print(f"   Expected: 1 (single speech session)")
            print(f"   Status: {'✅ PASS' if len(transcriptions) == 1 else '❌ FAIL'}")

            # Test 2: Multiple speech sessions with pauses
            print("\n📡 Test 2: Multiple Speech Sessions")
            print("-" * 40)

            transcriptions = []

            # First speech session
            print("🗣️  First speech session...")
            for i in range(0, len(speech_audio) // 2, chunk_size):
                chunk_data = speech_audio[i : i + chunk_size]
                vad_info = {"isSpeaking": True, "energy": 0.1, "confidence": 0.8}

                audio_chunk = stt_service.process_audio_with_vad(
                    chunk_data.tolist(), sample_rate, vad_info, time.time()
                )

                if audio_chunk:
                    result = await stt_service.transcribe_chunk(audio_chunk)
                    transcriptions.append(result.text)

            # End first session
            final_chunk = stt_service.process_audio_with_vad(
                [0.0] * 1000, sample_rate, {"isSpeaking": False}, time.time()
            )
            if final_chunk:
                result = await stt_service.transcribe_chunk(final_chunk)
                transcriptions.append(result.text)
                print(f"📝 First session: '{result.text}'")

            # Pause (silence)
            print("⏸️  Pause between sessions...")
            time.sleep(0.1)

            # Second speech session
            print("🗣️  Second speech session...")
            for i in range(len(speech_audio) // 2, len(speech_audio), chunk_size):
                chunk_data = speech_audio[i : i + chunk_size]
                vad_info = {"isSpeaking": True, "energy": 0.1, "confidence": 0.8}

                audio_chunk = stt_service.process_audio_with_vad(
                    chunk_data.tolist(), sample_rate, vad_info, time.time()
                )

                if audio_chunk:
                    result = await stt_service.transcribe_chunk(audio_chunk)
                    transcriptions.append(result.text)

            # End second session
            final_chunk = stt_service.process_audio_with_vad(
                [0.0] * 1000, sample_rate, {"isSpeaking": False}, time.time()
            )
            if final_chunk:
                result = await stt_service.transcribe_chunk(final_chunk)
                transcriptions.append(result.text)
                print(f"📝 Second session: '{result.text}'")

            print(f"\n📊 Test 2 Results:")
            print(f"   Total transcriptions: {len(transcriptions)}")
            print(f"   Expected: 2 (two separate speech sessions)")
            print(f"   Status: {'✅ PASS' if len(transcriptions) == 2 else '❌ FAIL'}")

            # Test 3: Short speech (below minimum duration)
            print("\n📡 Test 3: Short Speech (Below Minimum)")
            print("-" * 40)

            short_audio = speech_audio[: sample_rate // 4]  # 0.25 seconds
            transcriptions = []

            # Send short speech
            vad_info = {"isSpeaking": True, "energy": 0.1, "confidence": 0.8}
            audio_chunk = stt_service.process_audio_with_vad(
                short_audio.tolist(), sample_rate, vad_info, time.time()
            )

            # End session
            final_chunk = stt_service.process_audio_with_vad(
                [0.0] * 1000, sample_rate, {"isSpeaking": False}, time.time()
            )

            if final_chunk:
                result = await stt_service.transcribe_chunk(final_chunk)
                transcriptions.append(result.text)

            print(f"📊 Test 3 Results:")
            print(f"   Total transcriptions: {len(transcriptions)}")
            print(f"   Expected: 0 (speech too short)")
            print(f"   Status: {'✅ PASS' if len(transcriptions) == 0 else '❌ FAIL'}")

            print("\n🎉 Speech Session Testing Complete!")

    except Exception as e:
        print(f"❌ Error testing speech sessions: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_speech_sessions())
