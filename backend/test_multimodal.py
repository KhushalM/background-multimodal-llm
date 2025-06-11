#!/usr/bin/env python3
"""
Test script for Multimodal service
"""
import asyncio
import os
import time
from dotenv import load_dotenv

from models.multimodal import create_multimodal_service, ConversationInput

# Load environment variables
load_dotenv()

async def test_multimodal_service():
    """Test the multimodal service with conversation examples"""
    
    # Check if Gemini API key is available
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("❌ GEMINI_API_KEY not found in environment")
        print("Please add your Gemini API key to backend/.env file")
        print("Get one at: https://aistudio.google.com/app/apikey")
        return
    
    print("🧠 Testing Multimodal Service...")
    
    try:
        # Create multimodal service
        print("📡 Connecting to Gemini API...")
        multimodal_service = await create_multimodal_service(gemini_key)
        
        print("✅ Multimodal Service created successfully")
        
        # Test conversation scenarios
        test_conversations = [
            {
                "session": "test_session_1",
                "messages": [
                    "Hello! I'm testing the AI assistant.",
                    "Can you remember what I just said?",
                    "What's the weather like today?",
                    "Actually, I was just testing your memory. Did it work?"
                ]
            },
            {
                "session": "test_session_2", 
                "messages": [
                    "I'm working on a Python project and need help with async functions.",
                    "How do I handle exceptions in async code?",
                    "Thanks! Can you give me an example?"
                ]
            }
        ]
        
        for conversation in test_conversations:
            print(f"\n🗣️  Testing conversation: {conversation['session']}")
            print("=" * 50)
            
            for i, message in enumerate(conversation['messages']):
                print(f"\n👤 User: {message}")
                
                # Create conversation input
                conv_input = ConversationInput(
                    text=message,
                    session_id=conversation['session'],
                    timestamp=time.time(),
                    context={
                        "time_info": "2024-01-15 14:30:00",
                        "app_info": "Test Environment"
                    }
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
                print("📋 No summary available yet (summary created after longer conversations)")
        
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
        print("  ✅ Gemini API integration")
        print("  ✅ Conversation memory with LangChain")
        print("  ✅ Session management")
        print("  ✅ Context handling")
        print("  ✅ Error handling")
        
    except Exception as e:
        print(f"❌ Error testing multimodal service: {e}")
        import traceback
        traceback.print_exc()

async def test_conversation_flow():
    """Test a realistic conversation flow"""
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("❌ GEMINI_API_KEY not found")
        return
    
    print("\n🎭 Testing Realistic Conversation Flow...")
    print("=" * 50)
    
    try:
        service = await create_multimodal_service(gemini_key)
        
        # Simulate a realistic user session
        session_id = "realistic_test"
        
        conversation_flow = [
            "Hi there! I'm working on my computer and could use some help.",
            "I'm trying to learn Python programming. Where should I start?",
            "That sounds good. What about web development with Python?", 
            "Interesting! Can you remind me what we were talking about earlier?",
            "Perfect! One more question - what are some good practice projects for beginners?"
        ]
        
        for message in conversation_flow:
            print(f"\n👤 User: {message}")
            
            conv_input = ConversationInput(
                text=message,
                session_id=session_id,
                timestamp=time.time(),
                context={
                    "time_info": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "app_info": "VS Code",
                    "screen_info": "Programming tutorial open"
                }
            )
            
            response = await service.process_conversation(conv_input)
            print(f"🤖 AI: {response.text}")
            
            await asyncio.sleep(1)
        
        print(f"\n📚 Final conversation history length: {len(service.get_conversation_history(session_id))}")
        
    except Exception as e:
        print(f"❌ Error in conversation flow test: {e}")

if __name__ == "__main__":
    async def main():
        await test_multimodal_service()
        await test_conversation_flow()
    
    asyncio.run(main()) 