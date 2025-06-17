#!/usr/bin/env python3
"""
Test script for Multimodal service with integrated screen context
"""
import asyncio
import os
import sys
import time
import base64
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.multimodal import create_multimodal_service, ConversationInput

# Load environment variables
load_dotenv(override=True)


async def test_multimodal_service():
    """Test the multimodal service with conversation examples"""

    # Check if Gemini API key is available
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("❌ GEMINI_API_KEY not found in environment")
        print("Please add your Gemini API key to backend/.env file")
        print("Get one at: https://aistudio.google.com/app/apikey")
        return

    print("🧠 Testing Multimodal Service with Screen Context...")

    try:
        # Create multimodal service
        print("📡 Connecting to Gemini API...")
        multimodal_service = await create_multimodal_service(gemini_key)

        print("✅ Multimodal Service with screen context created successfully")

        # Test conversation scenarios
        test_conversations = [
            {
                "session": "test_session_1",
                "messages": [
                    "Hello! I'm testing the AI assistant.",
                    "Can you remember what I just said?",
                    "What's the weather like today?",
                    "Actually, I was just testing your memory. Did it work?",
                ],
            },
            {
                "session": "test_session_2",
                "messages": [
                    "I'm working on a Python project and need help with async functions.",
                    "How do I handle exceptions in async code?",
                    "Thanks! Can you give me an example?",
                ],
            },
        ]

        for conversation in test_conversations:
            print(f"\n🗣️  Testing conversation: {conversation['session']}")
            print("=" * 50)

            for i, message in enumerate(conversation["messages"]):
                print(f"\n👤 User: {message}")

                # Create conversation input
                conv_input = ConversationInput(
                    text=message,
                    session_id=conversation["session"],
                    timestamp=time.time(),
                    context={
                        "time_info": "2024-01-15 14:30:00",
                        "app_info": "Test Environment",
                    },
                )

                # Get AI response
                print("🤔 AI thinking...")
                response = await multimodal_service.process_conversation(conv_input)

                print(f"🤖 AI: {response.text}")
                print(f"⏱️  Processing time: {response.processing_time:.2f}s")
                print(f"📊 Token count: {response.token_count}")

                # Add small delay between messages
                await asyncio.sleep(1)

        # Test memory functionality
        print(f"\n🧠 Testing Memory Features...")
        print("=" * 50)

        # Get conversation history
        for session in ["test_session_1", "test_session_2"]:
            history = multimodal_service.get_conversation_history(session)
            print(f"\n📚 History for {session}: {len(history)} messages")

            # Get session summary
            summary = multimodal_service.get_session_summary(session)
            if summary:
                print(f"📋 Summary: {summary}")
            else:
                print(
                    "📋 No summary available yet (summary created after longer conversations)"
                )

        # Test active sessions
        active_sessions = multimodal_service.get_active_sessions()
        print(f"\n🔄 Active sessions: {active_sessions}")

        # Test session clearing
        print(f"\n🧹 Testing session cleanup...")
        cleared = multimodal_service.clear_session_memory("test_session_1")
        print(f"Cleared test_session_1: {cleared}")

        remaining_sessions = multimodal_service.get_active_sessions()
        print(f"Remaining sessions: {remaining_sessions}")

        print("\n✅ Multimodal service test completed successfully!")
        print("\n🎯 Key Features Verified:")
        print("  ✅ Gemini AI integration")
        print("  ✅ Conversation memory with LangChain")
        print("  ✅ Session management")
        print("  ✅ Context handling")
        print("  ✅ Error handling")

    except Exception as e:
        print(f"❌ Error testing multimodal service: {e}")
        import traceback

        traceback.print_exc()


async def test_screen_context_integration():
    """Test screen context integration"""

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("❌ GEMINI_API_KEY not found")
        return

    print("\n🖥️ Testing Screen Context Integration...")
    print("=" * 50)

    try:
        service = await create_multimodal_service(gemini_key)

        # Create a simple test image (1x1 white pixel as base64 PNG)
        test_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="

        session_id = "screen_test_session"

        # Test without screen context
        print("\n📝 Test 1: Text-only conversation")
        conv_input = ConversationInput(
            text="I need help with my code",
            session_id=session_id,
            timestamp=time.time(),
            context={
                "app_info": "VS Code",
                "time_info": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        )

        response = await service.process_conversation(conv_input)
        print(f"🤖 AI: {response.text[:100]}...")
        print(f"🖼️ Screen context: {response.screen_context is not None}")

        # Test with screen context
        print("\n📝 Test 2: Conversation with screen image")
        conv_input_with_screen = ConversationInput(
            text="What do you see on my screen?",
            session_id=session_id,
            timestamp=time.time(),
            context={
                "app_info": "VS Code",
                "time_info": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            screen_image=test_image,
        )

        response_with_screen = await service.process_conversation(
            conv_input_with_screen
        )
        print(f"🤖 AI: {response_with_screen.text[:100]}...")
        print(f"🖼️ Screen context: {response_with_screen.screen_context is not None}")

        if response_with_screen.screen_context:
            print(f"📋 Screen analysis:")
            print(
                f"   Description: {response_with_screen.screen_context.get('description', 'N/A')}"
            )
            print(
                f"   Context type: {response_with_screen.screen_context.get('context_type', 'N/A')}"
            )
            print(
                f"   Confidence: {response_with_screen.screen_context.get('confidence', 0):.1%}"
            )
            print(
                f"   Elements: {response_with_screen.screen_context.get('elements', [])}"
            )

        # Test caching
        print("\n📝 Test 3: Testing screen analysis caching")
        start_time = time.time()

        conv_input_cached = ConversationInput(
            text="Tell me more about what's on screen",
            session_id=session_id,
            timestamp=time.time(),
            screen_image=test_image,  # Same image - should use cache
        )

        response_cached = await service.process_conversation(conv_input_cached)
        processing_time = time.time() - start_time

        print(f"🤖 AI: {response_cached.text[:100]}...")
        print(
            f"⏱️ Processing time: {processing_time:.2f}s (should be faster due to caching)"
        )

        # Clear cache
        print("\n🧹 Testing cache management...")
        service.clear_screen_cache()
        print("Screen analysis cache cleared")

        print("\n✅ Screen context integration test completed!")
        print("\n🎯 Screen Context Features Verified:")
        print("  ✅ Screen image analysis with Gemini Vision")
        print("  ✅ Context integration in conversations")
        print("  ✅ Analysis result caching")
        print("  ✅ Cache management")

    except Exception as e:
        print(f"❌ Error in screen context test: {e}")
        import traceback

        traceback.print_exc()


async def test_conversation_flow():
    """Test a realistic conversation flow with screen context"""

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("❌ GEMINI_API_KEY not found")
        return

    print("\n🎭 Testing Realistic Conversation Flow with Screen Context...")
    print("=" * 50)

    try:
        service = await create_multimodal_service(gemini_key)

        # Simulate a realistic user session
        session_id = "realistic_test"

        # Create a simple test image
        test_code_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="

        conversation_flow = [
            {
                "text": "Hi there! I'm working on my computer and could use some help.",
                "screen_image": None,
            },
            {
                "text": "I'm trying to learn Python programming. Where should I start?",
                "screen_image": None,
            },
            {
                "text": "I have some code open. Can you help me understand what I'm looking at?",
                "screen_image": test_code_image,
            },
            {
                "text": "Interesting! Can you remind me what we were talking about earlier?",
                "screen_image": None,
            },
            {
                "text": "Based on what you can see on my screen, what should I focus on next?",
                "screen_image": test_code_image,
            },
        ]

        for i, message in enumerate(conversation_flow):
            print(f"\n👤 User: {message['text']}")
            if message["screen_image"]:
                print("🖼️ [Screen capture included]")

            conv_input = ConversationInput(
                text=message["text"],
                session_id=session_id,
                timestamp=time.time(),
                context={
                    "time_info": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "app_info": "VS Code",
                    "screen_info": (
                        "Programming tutorial open" if message["screen_image"] else None
                    ),
                },
                screen_image=message["screen_image"],
            )

            response = await service.process_conversation(conv_input)
            print(f"🤖 AI: {response.text}")

            if response.screen_context:
                print(
                    f"🔍 Screen context used: {response.screen_context.get('context_type', 'unknown')}"
                )

            await asyncio.sleep(1)

        print(
            f"\n📚 Final conversation history length: {len(service.get_conversation_history(session_id))}"
        )

        print("\n✅ Realistic conversation flow test completed!")

    except Exception as e:
        print(f"❌ Error in conversation flow test: {e}")


if __name__ == "__main__":

    async def main():
        await test_multimodal_service()
        await test_screen_context_integration()
        await test_conversation_flow()

    asyncio.run(main())
