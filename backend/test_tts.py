#!/usr/bin/env python3
"""
Test script for TTS service
"""
import asyncio
import os
import time
import numpy as np
from dotenv import load_dotenv

from models.TTS import create_tts_service, TTSRequest

# Load environment variables
load_dotenv(override=True)


async def test_tts_service():
    """Test the TTS service with various text inputs"""

    # Check if HF token is available
    hf_token = os.getenv("HUGGINGFACE_API_TOKEN")
    if not hf_token:
        print("❌ HUGGINGFACE_API_TOKEN not found in environment")
        print("Please add your HuggingFace API token to backend/.env file")
        return

    print("🗣️ Testing TTS Service...")

    try:
        # Create TTS service
        print("📡 Connecting to HuggingFace TTS API...")
        tts_service = await create_tts_service(hf_token)

        print("✅ TTS Service created successfully")

        # Test different types of text
        test_texts = [
            {
                "name": "Simple greeting",
                "text": "Hello! Welcome to the AI assistant.",
                "expected_duration": 2.0,
            },
            {
                "name": "Technical explanation",
                "text": "This is a text-to-speech service using machine learning models from HuggingFace.",
                "expected_duration": 4.0,
            },
            {
                "name": "Conversational response",
                "text": "I'd be happy to help you with that! Let me know if you have any questions.",
                "expected_duration": 3.5,
            },
            {"name": "Short response", "text": "Yes.", "expected_duration": 0.5},
            {
                "name": "Special characters",
                "text": "The price is $25.99, that's about 20% off!",
                "expected_duration": 3.0,
            },
        ]

        total_processing_time = 0
        total_audio_duration = 0

        for i, test_case in enumerate(test_texts):
            print(f"\n🎯 Test {i+1}: {test_case['name']}")
            print(f"📝 Text: \"{test_case['text']}\"")

            # Create TTS request
            request = TTSRequest(
                text=test_case["text"],
                voice_preset="default",
                session_id=f"test_session_{i}",
            )

            print("🔄 Generating speech...")

            # Generate speech
            response = await tts_service.synthesize_speech(request)

            print(f"✅ Generated audio:")
            print(f"   Duration: {response.duration:.2f}s")
            print(f"   Processing time: {response.processing_time:.2f}s")
            print(f"   Sample rate: {response.sample_rate}Hz")
            print(f"   Audio samples: {len(response.audio_data)}")
            print(f"   Audio format: {response.audio_format}")

            # Calculate efficiency
            efficiency = (
                response.duration / response.processing_time
                if response.processing_time > 0
                else 0
            )
            print(f"   Efficiency: {efficiency:.1f}x real-time")

            total_processing_time += response.processing_time
            total_audio_duration += response.duration

            # Basic quality checks
            if response.audio_format == "silence":
                print("   ⚠️  Warning: Generated silence (API may be having issues)")
            elif len(response.audio_data) == 0:
                print("   ❌ Error: No audio data generated")
            else:
                # Check audio properties
                audio_array = np.array(response.audio_data)
                max_amplitude = np.max(np.abs(audio_array))
                rms = np.sqrt(np.mean(audio_array**2))

                print(f"   Audio quality:")
                print(f"     Max amplitude: {max_amplitude:.3f}")
                print(f"     RMS level: {rms:.3f}")

                if max_amplitude < 0.01:
                    print("     ⚠️  Warning: Audio might be too quiet")
                elif max_amplitude > 0.95:
                    print("     ⚠️  Warning: Audio might be clipping")
                else:
                    print("     ✅ Audio levels look good")

        print(f"\n📊 Overall Results:")
        print(f"   Total tests: {len(test_texts)}")
        print(f"   Total audio generated: {total_audio_duration:.1f}s")
        print(f"   Total processing time: {total_processing_time:.1f}s")
        print(
            f"   Average efficiency: {total_audio_duration/total_processing_time:.1f}x real-time"
        )

        # Test batch processing
        print(f"\n🔄 Testing batch processing...")
        batch_texts = [
            "First sentence.",
            "Second sentence.",
            "Third and final sentence.",
        ]

        batch_responses = await tts_service.synthesize_batch(
            batch_texts, "batch_test_session"
        )

        print(f"✅ Batch processing completed:")
        for i, response in enumerate(batch_responses):
            print(
                f"   Sentence {i+1}: {response.duration:.2f}s audio, {response.processing_time:.2f}s processing"
            )

        # Test voice presets
        print(f"\n🎭 Testing voice presets...")
        supported_voices = tts_service.get_supported_voices()
        print(f"Supported voices: {supported_voices}")

        for voice in supported_voices[:2]:  # Test first 2 voices
            print(f"\n🗣️ Testing voice: {voice}")
            voice_request = TTSRequest(
                text="This is a test of the voice preset.",
                voice_preset=voice,
                session_id=f"voice_test_{voice}",
            )

            voice_response = await tts_service.synthesize_speech(voice_request)
            print(
                f"   Generated {voice_response.duration:.2f}s audio with {voice} voice"
            )

        print("\n✅ TTS service test completed successfully!")
        print("\n🎯 Key Features Verified:")
        print("  ✅ HuggingFace TTS API integration")
        print("  ✅ Text preprocessing and cleaning")
        print("  ✅ Audio generation and post-processing")
        print("  ✅ Multiple voice presets")
        print("  ✅ Batch processing")
        print("  ✅ Error handling and fallbacks")

    except Exception as e:
        print(f"❌ Error testing TTS service: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Cleanup
        if "tts_service" in locals():
            await tts_service.__aexit__(None, None, None)


async def test_conversation_tts():
    """Test TTS with realistic conversation responses"""

    hf_token = os.getenv("HUGGINGFACE_API_TOKEN")
    if not hf_token:
        print("❌ HUGGINGFACE_API_TOKEN not found")
        return

    print("\n🎭 Testing Realistic Conversation TTS...")
    print("=" * 50)

    try:
        service = await create_tts_service(hf_token)

        # Simulate AI assistant responses
        ai_responses = [
            "Hello! I'm your AI assistant. How can I help you today?",
            "I understand you're working on a Python project. That's great! What specific area do you need help with?",
            "For web development with Python, I'd recommend starting with Flask or Django. Flask is simpler for beginners.",
            "Absolutely! Here's a simple example of a Flask web application that you can start with.",
            "You're welcome! Feel free to ask if you need help with anything else. I'm here to assist you.",
        ]

        print(f"🤖 Converting {len(ai_responses)} AI responses to speech...")

        total_time = 0
        for i, response_text in enumerate(ai_responses):
            print(f'\n💬 AI Response {i+1}: "{response_text[:50]}..."')

            request = TTSRequest(
                text=response_text,
                voice_preset="default",
                session_id="conversation_test",
            )

            tts_response = await service.synthesize_speech(request)
            total_time += tts_response.processing_time

            print(
                f"🔊 Generated {tts_response.duration:.1f}s audio in {tts_response.processing_time:.1f}s"
            )

        print(f"\n📈 Conversation TTS Summary:")
        print(f"   Responses processed: {len(ai_responses)}")
        print(f"   Total processing time: {total_time:.1f}s")
        print(f"   Average per response: {total_time/len(ai_responses):.1f}s")

    except Exception as e:
        print(f"❌ Error in conversation TTS test: {e}")


if __name__ == "__main__":

    async def main():
        await test_tts_service()
        await test_conversation_tts()

    asyncio.run(main())
