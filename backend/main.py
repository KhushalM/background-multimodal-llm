#!/usr/bin/env python3
"""
Background Multimodal LLM Backend Server
Handles WebSocket connections for screen sharing and voice assistant functionality.
"""

import json
import logging
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
logger.info(
    "CORS middleware configured with allow_origins=['http://localhost:3000', 'http://127.0.0.1:3000']"
)


# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_attempts: Dict[WebSocket, int] = {}
        logger.info("ConnectionManager initialized")

    async def connect(self, websocket: WebSocket):
        try:
            logger.info(
                f"Attempting to accept WebSocket connection from {websocket.client.host}"
            )
            await websocket.accept()
            self.active_connections.append(websocket)
            self.connection_attempts[websocket] = 0
            logger.info(
                f"WebSocket connection accepted from {websocket.client.host}. Total connections: {len(self.active_connections)}"
            )
        except Exception as e:
            logger.error(f"Failed to accept WebSocket connection: {str(e)}")
            raise

    def disconnect(self, websocket: WebSocket):
        try:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            if websocket in self.connection_attempts:
                del self.connection_attempts[websocket]
            logger.info(
                f"Client disconnected. Total connections: {len(self.active_connections)}"
            )
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket: {e}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            if websocket in self.active_connections:
                # Check if websocket is still open before sending
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(message)
                else:
                    logger.warning(
                        "Attempted to send message to disconnected websocket"
                    )
                    self.disconnect(websocket)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            # Only disconnect if we've had multiple failures
            self.connection_attempts[websocket] = (
                self.connection_attempts.get(websocket, 0) + 1
            )
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
                self.connection_attempts[connection] = (
                    self.connection_attempts.get(connection, 0) + 1
                )
                if self.connection_attempts[connection] >= 3:
                    logger.warning(f"Too many broadcast failures, disconnecting client")
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
            "multimodal_with_screen_context": service_manager.get_multimodal_service()
            is not None,
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

                logger.info(
                    f"Processing WebSocket message - Type: {message_type}, Timestamp: {timestamp}"
                )

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

    # Send acknowledgment back to client
    response = {
        "type": "screen_share_started",
        "message": "Screen sharing session initiated",
        "timestamp": datetime.now().timestamp(),
    }

    await manager.send_personal_message(json.dumps(response), websocket)


async def handle_screen_share_stop(websocket: WebSocket, message: Dict[str, Any]):
    """Handle screen sharing stop event."""
    logger.info("Screen sharing stopped")

    # Send acknowledgment back to client
    response = {
        "type": "screen_share_stopped",
        "message": "Screen sharing session ended",
        "timestamp": datetime.now().timestamp(),
    }

    await manager.send_personal_message(json.dumps(response), websocket)


async def handle_voice_assistant_start(websocket: WebSocket, message: Dict[str, Any]):
    """Handle voice assistant start event."""
    logger.info("Voice assistant started")

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

    logger.debug(
        f"Received audio data: {len(audio_data)} samples at {timestamp}, "
        f"VAD: {vad_info}"
    )
    if screen_image:
        logger.debug("Screen image included with audio data")

    # Get STT service
    stt_service = service_manager.get_stt_service()
    if not stt_service:
        logger.warning("STT service not available")
        return

    try:
        # Process audio with VAD information to manage speech sessions
        audio_chunk = stt_service.process_audio_with_vad(
            audio_data, sample_rate, vad_info, timestamp
        )

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

                # Send transcription to multimodal LLM for processing (with optional screen context)
                await process_with_multimodal_llm(
                    websocket, transcription.text, transcription.timestamp, screen_image
                )

            else:
                logger.debug("Empty transcription result")
        else:
            # Audio is being accumulated in current speech session
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

    logger.debug(f"Received VAD state: {vad_info} at {timestamp}")

    # Get STT service
    stt_service = service_manager.get_stt_service()
    if not stt_service:
        logger.warning("STT service not available")
        return

    try:
        # Process VAD state change (typically silence) to potentially end speech sessions
        audio_chunk = stt_service.process_audio_with_vad(
            [], 16000, vad_info, timestamp  # Empty audio data for state-only updates
        )

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

                # Send transcription to multimodal LLM for processing
                await process_with_multimodal_llm(
                    websocket, transcription.text, transcription.timestamp
                )

            else:
                logger.debug("Empty transcription result from silence-ended session")

    except Exception as e:
        logger.error(f"Error processing VAD state: {e}")

        # Send error response
        response = {
            "type": "error",
            "message": f"VAD state processing error: {str(e)}",
            "timestamp": datetime.now().timestamp(),
        }

        await manager.send_personal_message(json.dumps(response), websocket)


async def process_with_multimodal_llm(
    websocket: WebSocket, text: str, timestamp: float, screen_image: str = None
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
        async with PerformanceTimer(
            performance_monitor, "multimodal", "process_conversation"
        ):
            ai_response = await multimodal_service.process_conversation(
                conversation_input
            )

        logger.info(f"AI Response: {ai_response.text}")

        # Send AI response back to client (including screen context if available)
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
        tts_request = TTSRequest(
            text=text, voice_preset="default", session_id=session_id
        )

        # Generate speech with performance monitoring
        async with PerformanceTimer(performance_monitor, "tts", "synthesize_speech"):
            tts_response = await tts_service.synthesize_speech(tts_request)

        logger.info(
            f"Generated {tts_response.duration:.2f}s of speech in {tts_response.processing_time:.2f}s"
        )

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
            logger.error(
                f"Failed to send TTS audio response (connection likely closed): {send_error}"
            )

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
            logger.error(
                f"Failed to send TTS error response (connection likely closed): {send_error}"
            )


if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",
        access_log=True,
    )
