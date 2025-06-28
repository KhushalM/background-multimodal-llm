#!/usr/bin/env python3
"""
Background Multimodal LLM Backend Server
Handles WebSocket connections for screen sharing and voice assistant functionality.
"""

# Load environment variables first
import pathlib
from dotenv import load_dotenv

# Load environment variables from .env file
current_dir = pathlib.Path(__file__).parent
env_path = current_dir / ".env"
load_dotenv(dotenv_path=env_path)

import json
import logging
import time
from typing import Dict, List, Any
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketState
import uvicorn

from services.service_manager import service_manager
from services.performance_monitor import performance_monitor, PerformanceTimer
from models.multimodal import ConversationInput
from models.TTS import TTSRequest

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# FastAPI app instance
app = FastAPI(
    title="Background Multimodal LLM API",
    description="WebSocket server for screen sharing and voice assistant with integrated screen context",
    version="1.0.0",
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await service_manager.initialize_services()
    logger.info("All services initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on shutdown"""
    await service_manager.cleanup_services()
    logger.info("All services cleaned up")


# Note: Removed custom signal handlers to let uvicorn handle shutdown naturally
# This prevents interference with the cleanup process


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],  # Frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Log CORS configuration
logger.info("CORS middleware configured with allow_origins=['http://localhost:3000', 'http://127.0.0.1:3000']")


# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_attempts: Dict[WebSocket, int] = {}
        # Track session states for each connection
        self.session_states: Dict[WebSocket, Dict[str, Any]] = {}
        logger.info("ConnectionManager initialized")

    async def connect(self, websocket: WebSocket):
        try:
            logger.info(f"Attempting to accept WebSocket connection from {websocket.client.host if websocket.client else 'unknown'}")
            await websocket.accept()
            self.active_connections.append(websocket)
            self.connection_attempts[websocket] = 0
            # Initialize session state
            self.session_states[websocket] = {
                "screen_share_on": False,
                "voice_assistant_on": False,
            }
            logger.info(f"WebSocket connection accepted from {websocket.client.host if websocket.client else 'unknown'}. Total connections: {len(self.active_connections)}")
        except Exception as e:
            logger.error(f"Failed to accept WebSocket connection: {str(e)}")
            raise

    def disconnect(self, websocket: WebSocket):
        try:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            if websocket in self.connection_attempts:
                del self.connection_attempts[websocket]
            if websocket in self.session_states:
                del self.session_states[websocket]
            logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket: {e}")

    def get_session_state(self, websocket: WebSocket) -> Dict[str, Any]:
        """Get session state for a WebSocket connection"""
        return self.session_states.get(
            websocket,
            {
                "screen_share_on": False,
                "voice_assistant_on": False,
            },
        )

    def update_session_state(self, websocket: WebSocket, key: str, value: Any):
        """Update session state for a WebSocket connection"""
        if websocket not in self.session_states:
            self.session_states[websocket] = {
                "screen_share_on": False,
                "voice_assistant_on": False,
            }
        self.session_states[websocket][key] = value
        logger.debug(f"Updated session state: {key}={value}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            if websocket in self.active_connections:
                # Check if websocket is still open before sending
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(message)
                else:
                    logger.warning("Attempted to send message to disconnected websocket")
                    self.disconnect(websocket)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            # Only disconnect if we've had multiple failures
            self.connection_attempts[websocket] = self.connection_attempts.get(websocket, 0) + 1
            if self.connection_attempts[websocket] >= 3:
                logger.warning("Too many send failures, disconnecting client")
                self.disconnect(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections[:]:  # Create a copy of the list
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                # Only disconnect if we've had multiple failures
                self.connection_attempts[connection] = self.connection_attempts.get(connection, 0) + 1
                if self.connection_attempts[connection] >= 3:
                    logger.warning("Too many broadcast failures, disconnecting client")
                    self.disconnect(connection)


manager = ConnectionManager()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Background Multimodal LLM API",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "active_connections": len(manager.active_connections),
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "stt": service_manager.get_stt_service() is not None,
            "multimodal_with_screen_context": service_manager.get_multimodal_service() is not None,
            "tts": service_manager.get_tts_service() is not None,
            "ready": service_manager.is_ready(),
            "fully_ready": service_manager.is_fully_ready(),
        },
        "performance": performance_monitor.get_performance_summary(),
    }


@app.get("/performance")
async def get_performance():
    """Get detailed performance metrics and optimization recommendations."""
    return {
        "timestamp": datetime.now().isoformat(),
        "summary": performance_monitor.get_performance_summary(),
        "recommendations": performance_monitor.get_optimization_recommendations(),
        "optimizations": performance_monitor.optimizations,
    }


@app.post("/performance/optimize")
async def optimize_performance():
    """Apply automatic performance optimizations."""
    result = performance_monitor.optimize_automatically()
    return {"timestamp": datetime.now().isoformat(), "optimization_result": result}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for handling screen sharing and voice assistant data."""
    logger.info("WebSocket connection attempt received at /ws endpoint")
    try:
        await manager.connect(websocket)
        logger.info("WebSocket connection established successfully")
    except Exception as e:
        logger.error(f"Failed to establish WebSocket connection: {str(e)}")
        return

    try:
        while True:
            # Wait for message from client
            data = await websocket.receive_text()

            try:
                # Parse the JSON message
                message = json.loads(data)
                message_type = message.get("type")
                timestamp = message.get("timestamp", datetime.now().timestamp())

                logger.info(f"Processing WebSocket message - Type: {message_type}, Timestamp: {timestamp}")

                # Handle different message types
                if message_type == "screen_share_start":
                    logger.info("Handling screen share start request")
                    await handle_screen_share_start(websocket, message)

                elif message_type == "screen_share_stop":
                    logger.info("Handling screen share stop request")
                    await handle_screen_share_stop(websocket, message)

                elif message_type == "voice_assistant_start":
                    logger.info("Handling voice assistant start request")
                    await handle_voice_assistant_start(websocket, message)

                elif message_type == "voice_assistant_stop":
                    logger.info("Handling voice assistant stop request")
                    await handle_voice_assistant_stop(websocket, message)

                elif message_type == "audio_data":
                    logger.info("Handling audio data request")
                    await handle_audio_data(websocket, message)

                elif message_type == "vad_state":
                    logger.debug("Handling VAD state update")
                    await handle_vad_state(websocket, message)

                elif message_type == "screen_capture_response":
                    logger.info("Handling screen capture response")
                    await handle_screen_capture_response(websocket, message)

                elif message_type == "heartbeat":
                    logger.debug("Received heartbeat, sending pong")
                    await manager.send_personal_message(
                        json.dumps(
                            {
                                "type": "heartbeat_pong",
                                "timestamp": datetime.now().timestamp(),
                            }
                        ),
                        websocket,
                    )

                else:
                    logger.warning(f"Unknown message type received: {message_type}")
                    await manager.send_personal_message(
                        json.dumps(
                            {
                                "type": "error",
                                "message": f"Unknown message type: {message_type}",
                                "timestamp": datetime.now().timestamp(),
                            }
                        ),
                        websocket,
                    )

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse WebSocket message as JSON: {e}")
                await manager.send_personal_message(
                    json.dumps(
                        {
                            "type": "error",
                            "message": "Invalid JSON format",
                            "timestamp": datetime.now().timestamp(),
                        }
                    ),
                    websocket,
                )

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Unexpected error in WebSocket handler: {e}")
        logger.error(f"WebSocket state: {websocket.client_state}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        manager.disconnect(websocket)


async def handle_screen_share_start(websocket: WebSocket, message: Dict[str, Any]):
    """Handle screen sharing start event."""
    logger.info("Screen sharing started")

    # Update session state
    manager.update_session_state(websocket, "screen_share_on", True)

    # Send acknowledgment back to client
    response = {
        "type": "screen_share_started",
        "message": "Screen sharing session initiated",
        "timestamp": datetime.now().timestamp(),
        "screen_share_on": True,
    }

    await manager.send_personal_message(json.dumps(response), websocket)


async def handle_screen_share_stop(websocket: WebSocket, message: Dict[str, Any]):
    """Handle screen sharing stop event."""
    logger.info("Screen sharing stopped")

    # Update session state
    manager.update_session_state(websocket, "screen_share_on", False)

    # Send acknowledgment back to client
    response = {
        "type": "screen_share_stopped",
        "message": "Screen sharing session ended",
        "timestamp": datetime.now().timestamp(),
        "screen_share_on": False,
    }

    await manager.send_personal_message(json.dumps(response), websocket)


async def handle_voice_assistant_start(websocket: WebSocket, message: Dict[str, Any]):
    """Handle voice assistant start event."""
    logger.info("Voice assistant started")

    # Update session state
    manager.update_session_state(websocket, "voice_assistant_on", True)

    # Send acknowledgment back to client
    response = {
        "type": "voice_assistant_started",
        "message": "Voice assistant activated",
        "timestamp": datetime.now().timestamp(),
    }

    await manager.send_personal_message(json.dumps(response), websocket)


async def handle_voice_assistant_stop(websocket: WebSocket, message: Dict[str, Any]):
    """Handle voice assistant stop event."""
    logger.info("Voice assistant stopped")

    # Update session state
    manager.update_session_state(websocket, "voice_assistant_on", False)

    # Send acknowledgment back to client
    response = {
        "type": "voice_assistant_stopped",
        "message": "Voice assistant deactivated",
        "timestamp": datetime.now().timestamp(),
    }

    await manager.send_personal_message(json.dumps(response), websocket)


async def handle_audio_data(websocket: WebSocket, message: Dict[str, Any]):
    """Handle incoming audio data from voice assistant."""
    audio_data = message.get("data", [])
    timestamp = message.get("timestamp")
    sample_rate = message.get("sample_rate", 16000)
    vad_info = message.get("vad", {})  # VAD information from frontend
    screen_image = message.get("screen_image")  # Optional screen capture

    logger.debug(f"Received audio data: {len(audio_data)} samples at {timestamp}, " f"VAD: {vad_info}")
    if screen_image:
        logger.debug("Screen image included with audio data")

    # Get STT service
    stt_service = service_manager.get_stt_service()
    if not stt_service:
        logger.warning("STT service not available")
        return

    try:
        # Add debug logging for VAD processing
        logger.info(f"Processing audio with VAD - samples: {len(audio_data)}, VAD info: {vad_info}")

        # Process audio with VAD information to manage speech sessions
        audio_chunk = stt_service.process_audio_with_vad(audio_data, sample_rate, vad_info, timestamp)

        logger.info(f"VAD processing result - audio_chunk returned: {audio_chunk is not None}")

        if audio_chunk:
            # We have a complete speech session ready for transcription
            logger.info("Transcribing complete speech session...")
            async with PerformanceTimer(performance_monitor, "stt", "transcribe_chunk"):
                transcription = await stt_service.transcribe_chunk(audio_chunk)

            if transcription.text:
                logger.info(f"Transcription: {transcription.text}")

                # Send transcription back to client
                response = {
                    "type": "transcription_result",
                    "text": transcription.text,
                    "timestamp": transcription.timestamp,
                    "processing_time": transcription.processing_time,
                    "confidence": transcription.confidence,
                }

                await manager.send_personal_message(json.dumps(response), websocket)

                # Use new flow that checks for screen triggers first
                await handle_transcription_with_screen_check(websocket, transcription.text, transcription.timestamp, screen_image)

            else:
                logger.debug("Empty transcription result")
        else:
            # Audio is being accumulated in current speech session
            logger.info(f"Audio being accumulated - VAD isSpeaking: {vad_info.get('isSpeaking', False)}")
            # Optionally send partial feedback to client
            if vad_info.get("isSpeaking", False):
                response = {
                    "type": "speech_active",
                    "message": "Speech detected, accumulating audio...",
                    "timestamp": datetime.now().timestamp(),
                    "vad": vad_info,
                }
                await manager.send_personal_message(json.dumps(response), websocket)

    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        import traceback

        logger.error(f"Audio processing traceback: {traceback.format_exc()}")

        # Send error response
        response = {
            "type": "error",
            "message": f"Audio processing error: {str(e)}",
            "timestamp": datetime.now().timestamp(),
        }

        await manager.send_personal_message(json.dumps(response), websocket)


async def handle_vad_state(websocket: WebSocket, message: Dict[str, Any]):
    """Handle VAD state updates (silence notifications) from frontend."""
    timestamp = message.get("timestamp")
    vad_info = message.get("vad", {})

    logger.info(f"Received VAD state: {vad_info} at {timestamp}")

    # Get STT service
    stt_service = service_manager.get_stt_service()
    if not stt_service:
        logger.warning("STT service not available")
        return

    try:
        # Process VAD state change (typically silence) to potentially end speech sessions
        logger.info(f"Processing VAD state change - VAD info: {vad_info}")
        audio_chunk = stt_service.process_audio_with_vad([], 16000, vad_info, timestamp)  # Empty audio data for state-only updates

        logger.info(f"VAD state processing result - audio_chunk returned: {audio_chunk is not None}")

        if audio_chunk:
            # Speech session ended due to silence
            logger.info("Speech session ended due to silence detection")
            async with PerformanceTimer(performance_monitor, "stt", "transcribe_chunk"):
                transcription = await stt_service.transcribe_chunk(audio_chunk)

            if transcription.text:
                logger.info(f"Transcription: {transcription.text}")

                # Send transcription back to client
                response = {
                    "type": "transcription_result",
                    "text": transcription.text,
                    "timestamp": transcription.timestamp,
                    "processing_time": transcription.processing_time,
                    "confidence": transcription.confidence,
                }

                await manager.send_personal_message(json.dumps(response), websocket)

                # Use new flow that checks for screen triggers first
                await handle_transcription_with_screen_check(websocket, transcription.text, transcription.timestamp)

            else:
                logger.debug("Empty transcription result from silence-ended session")
        else:
            logger.info("VAD state change - no speech session to complete")

    except Exception as e:
        logger.error(f"Error processing VAD state: {e}")
        import traceback

        logger.error(f"VAD state processing traceback: {traceback.format_exc()}")

        # Send error response
        response = {
            "type": "error",
            "message": f"VAD state processing error: {str(e)}",
            "timestamp": datetime.now().timestamp(),
        }

        await manager.send_personal_message(json.dumps(response), websocket)


def check_text_for_screen_triggers(text: str) -> Dict[str, Any]:
    """Check if text contains triggers that would benefit from screen capture"""
    text_lower = text.lower()

    # Explicit screen-related trigger words
    explicit_triggers = [
        "screen",
        "display",
        "see",
        "look",
        "show",
        "what's on",
        "what is on",
        "current page",
        "this page",
        "this screen",
        "my screen",
        "the screen",
        "what am i",
        "where am i",
        "help with this",
        "help me with this",
        "what do you see",
        "can you see",
        "describe",
        "read this",
    ]

    # Context words that suggest user needs help with current content
    context_words = [
        "error",
        "issue",
        "problem",
        "bug",
        "broken",
        "not working",
        "help",
        "stuck",
        "confused",
        "understand",
        "explain",
        "debug",
        "fix",
    ]

    # Question indicators that often pair with screen context
    question_indicators = [
        "what",
        "how",
        "where",
        "why",
        "which",
        "when",
        "can you",
        "could you",
        "would you",
        "should i",
        "do i",
        "am i",
        "is this",
    ]

    # Find matches
    trigger_matches = [trigger for trigger in explicit_triggers if trigger in text_lower]
    context_matches = [word for word in context_words if word in text_lower]
    question_matches = [q for q in question_indicators if text_lower.startswith(q) or f" {q}" in text_lower]

    # Calculate confidence based on matches
    confidence = 0.0
    reason = "no_triggers"

    if trigger_matches:
        confidence = 0.9
        reason = "explicit_trigger"
    elif context_matches and question_matches:
        confidence = 0.8
        reason = "context_question"
    elif context_matches and len(text_lower.split()) > 3:
        confidence = 0.6
        reason = "context_phrase"
    elif question_matches and len(text_lower.split()) > 4:
        confidence = 0.5
        reason = "general_question"

    should_capture = confidence >= 0.6

    return {
        "should_capture": should_capture,
        "confidence": confidence,
        "reason": reason,
        "trigger_matches": trigger_matches,
        "context_matches": context_matches,
        "question_matches": question_matches,
        "text_length": len(text_lower.split()),
    }


async def handle_transcription_with_screen_check(
    websocket: WebSocket,
    text: str,
    timestamp: float,
    screen_image: str = None,
):
    """Handle transcription and check if we need screen capture before multimodal processing"""

    # First check if we already have a screen image
    if screen_image:
        logger.info("Screen image already provided, proceeding to multimodal processing")
        await process_with_multimodal_llm(websocket, text, timestamp, screen_image)
        return

    # Get session state to check if screen sharing is active
    session_state = manager.get_session_state(websocket)
    screen_share_on = session_state.get("screen_share_on", False)

    # Check if the text contains trigger words that would benefit from screen capture
    if screen_share_on:
        needs_screen_capture = check_text_for_screen_triggers(text)
    else:
        needs_screen_capture = {
            "should_capture": False,
            "confidence": 0.0,
            "reason": "screen_share_off",
        }
    logger.info(f"Screen share on: {screen_share_on}")
    logger.info(f"Needs screen capture: {needs_screen_capture}")

    if needs_screen_capture["should_capture"] and needs_screen_capture["confidence"] >= 0.6:
        logger.info(f"Screen capture recommended for text: '{text}' (confidence: {needs_screen_capture['confidence']:.2f})")

        # Send screen capture request to frontend and store the context for later
        screen_request = {
            "type": "screen_capture_request",
            "confidence": needs_screen_capture["confidence"],
            "reason": needs_screen_capture["reason"],
            "trigger_matches": needs_screen_capture["trigger_matches"],
            "context_matches": needs_screen_capture["context_matches"],
            "timestamp": datetime.now().timestamp(),
            "original_text": text,
            "original_timestamp": timestamp,
        }

        logger.info(f"Requesting screen capture: {needs_screen_capture['reason']} (confidence: {needs_screen_capture['confidence']:.2f})")
        await manager.send_personal_message(json.dumps(screen_request), websocket)

        # Don't process with multimodal LLM yet - wait for screen capture response
        return
    else:
        # No screen capture needed, proceed with text-only processing
        logger.info("No screen capture needed, proceeding with text-only processing")
        await process_with_multimodal_llm(websocket, text, timestamp, None)


async def handle_screen_capture_response(websocket: WebSocket, message: Dict[str, Any]):
    """Handle screen capture response from frontend"""
    screen_image = message.get("screen_image")
    original_text = message.get("original_text", "")
    request_data = message.get("request_data", {})
    original_timestamp = request_data.get("original_timestamp")
    if not original_timestamp:
        original_timestamp = message.get("timestamp", time.time())

    logger.info(f"Screen capture response - has image: {bool(screen_image)}, " f"original_text: '{original_text}', message keys: {list(message.keys())}")

    if screen_image and original_text:
        logger.info("Received screen capture, processing with visual context")

        # Process with the original transcription timestamp for proper session continuity
        await process_with_multimodal_llm(websocket, original_text, original_timestamp, screen_image)
    else:
        logger.warning(f"Invalid screen capture response - screen_image present: " f"{bool(screen_image)}, original_text: '{original_text}'")


async def process_with_multimodal_llm(
    websocket: WebSocket,
    text: str,
    timestamp: float,
    screen_image: str = None,
):
    """Process transcribed text with the multimodal LLM (with optional screen context)"""
    try:
        # Get multimodal service
        multimodal_service = service_manager.get_multimodal_service()
        if not multimodal_service:
            logger.warning("Multimodal service not available")
            return

        # Create conversation input
        # Use websocket ID as session ID for now (you might want a more sophisticated session management)
        session_id = f"ws_{id(websocket)}"

        conversation_input = ConversationInput(
            text=text,
            session_id=session_id,
            timestamp=timestamp,
            context={
                "time_info": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "app_info": "Background Multimodal Assistant",
            },
            screen_image=screen_image,  # Include screen image if available
        )

        logger.info(f"Processing with multimodal LLM: {text}")
        if screen_image:
            logger.info("Including screen context in conversation processing")

        # Generate AI response with performance monitoring (includes screen analysis if image provided)
        async with PerformanceTimer(performance_monitor, "multimodal", "process_conversation"):
            ai_response = await multimodal_service.process_conversation(conversation_input)

        logger.info(f"AI Response: {ai_response.text}")

        # Screen capture requests are now handled before calling this function
        # so we don't need to handle them here anymore

        # Send AI response back to client
        response = {
            "type": "ai_response",
            "text": ai_response.text,
            "timestamp": ai_response.timestamp,
            "processing_time": ai_response.processing_time,
            "session_id": ai_response.session_id,
        }

        # Include screen context in response if available
        if ai_response.screen_context:
            response["screen_context"] = ai_response.screen_context

        await manager.send_personal_message(json.dumps(response), websocket)

        # Convert AI response to speech
        await process_with_tts(websocket, ai_response.text, ai_response.session_id)

    except Exception as e:
        logger.error(f"Error processing with multimodal LLM: {e}")

        # Send error response
        error_response = {
            "type": "error",
            "message": f"AI processing error: {str(e)}",
            "timestamp": datetime.now().timestamp(),
        }

        await manager.send_personal_message(json.dumps(error_response), websocket)


async def process_with_tts(websocket: WebSocket, text: str, session_id: str):
    """Convert AI response text to speech"""
    try:
        # Get TTS service
        tts_service = service_manager.get_tts_service()
        if not tts_service:
            logger.warning("TTS service not available")
            return

        logger.info(f"Converting to speech: {text[:100]}...")

        # Create TTS request
        tts_request = TTSRequest(text=text, voice_preset="default", session_id=session_id)

        # Generate speech with performance monitoring
        async with PerformanceTimer(performance_monitor, "tts", "synthesize_speech"):
            tts_response = await tts_service.synthesize_speech(tts_request)

        logger.info(f"Generated {tts_response.duration:.2f}s of speech in {tts_response.processing_time:.2f}s")

        # Send audio response back to client
        audio_response = {
            "type": "audio_response",
            "audio_data": tts_response.audio_data,
            "sample_rate": tts_response.sample_rate,
            "duration": tts_response.duration,
            "processing_time": tts_response.processing_time,
            "text": tts_response.text,
            "timestamp": datetime.now().timestamp(),
            "session_id": session_id,
        }

        # Check if websocket is still connected before sending TTS response
        try:
            await manager.send_personal_message(json.dumps(audio_response), websocket)
        except Exception as send_error:
            logger.error(f"Failed to send TTS audio response (connection likely closed): {send_error}")

    except Exception as e:
        logger.error(f"Error processing with TTS: {e}")

        # Check if websocket is still connected before sending error
        try:
            error_response = {
                "type": "error",
                "message": f"TTS processing error: {str(e)}",
                "timestamp": datetime.now().timestamp(),
            }
            await manager.send_personal_message(json.dumps(error_response), websocket)
        except Exception as send_error:
            logger.error(f"Failed to send TTS error response (connection likely closed): {send_error}")


if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,  # Changed from 8000 to 8001
        reload=True,
        log_level="debug",
        access_log=True,
    )
