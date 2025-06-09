#!/usr/bin/env python3
"""
Background Multimodal LLM Backend Server
Handles WebSocket connections for screen sharing and voice assistant functionality.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app instance
app = FastAPI(
    title="Background Multimodal LLM API",
    description="WebSocket server for screen sharing and voice assistant",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")
        
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
        
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")

manager = ConnectionManager()

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Background Multimodal LLM API",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "active_connections": len(manager.active_connections)
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for handling screen sharing and voice assistant data."""
    await manager.connect(websocket)
    
    try:
        while True:
            # Wait for message from client
            data = await websocket.receive_text()
            
            try:
                # Parse the JSON message
                message = json.loads(data)
                message_type = message.get("type")
                timestamp = message.get("timestamp", datetime.now().timestamp())
                
                logger.info(f"Received message type: {message_type}")
                
                # Handle different message types
                if message_type == "screen_share_start":
                    await handle_screen_share_start(websocket, message)
                    
                elif message_type == "screen_share_stop":
                    await handle_screen_share_stop(websocket, message)
                    
                elif message_type == "voice_assistant_start":
                    await handle_voice_assistant_start(websocket, message)
                    
                elif message_type == "voice_assistant_stop":
                    await handle_voice_assistant_stop(websocket, message)
                    
                elif message_type == "audio_data":
                    await handle_audio_data(websocket, message)
                    
                else:
                    logger.warning(f"Unknown message type: {message_type}")
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "error",
                            "message": f"Unknown message type: {message_type}",
                            "timestamp": datetime.now().timestamp()
                        }),
                        websocket
                    )
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {e}")
                await manager.send_personal_message(
                    json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format",
                        "timestamp": datetime.now().timestamp()
                    }),
                    websocket
                )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected")

async def handle_screen_share_start(websocket: WebSocket, message: Dict[str, Any]):
    """Handle screen sharing start event."""
    logger.info("Screen sharing started")
    
    # Send acknowledgment back to client
    response = {
        "type": "screen_share_started",
        "message": "Screen sharing session initiated",
        "timestamp": datetime.now().timestamp()
    }
    
    await manager.send_personal_message(json.dumps(response), websocket)

async def handle_screen_share_stop(websocket: WebSocket, message: Dict[str, Any]):
    """Handle screen sharing stop event."""
    logger.info("Screen sharing stopped")
    
    # Send acknowledgment back to client
    response = {
        "type": "screen_share_stopped",
        "message": "Screen sharing session ended",
        "timestamp": datetime.now().timestamp()
    }
    
    await manager.send_personal_message(json.dumps(response), websocket)

async def handle_voice_assistant_start(websocket: WebSocket, message: Dict[str, Any]):
    """Handle voice assistant start event."""
    logger.info("Voice assistant started")
    
    # Send acknowledgment back to client
    response = {
        "type": "voice_assistant_started",
        "message": "Voice assistant activated",
        "timestamp": datetime.now().timestamp()
    }
    
    await manager.send_personal_message(json.dumps(response), websocket)

async def handle_voice_assistant_stop(websocket: WebSocket, message: Dict[str, Any]):
    """Handle voice assistant stop event."""
    logger.info("Voice assistant stopped")
    
    # Send acknowledgment back to client
    response = {
        "type": "voice_assistant_stopped",
        "message": "Voice assistant deactivated",
        "timestamp": datetime.now().timestamp()
    }
    
    await manager.send_personal_message(json.dumps(response), websocket)

async def handle_audio_data(websocket: WebSocket, message: Dict[str, Any]):
    """Handle incoming audio data from voice assistant."""
    audio_data = message.get("data", [])
    timestamp = message.get("timestamp")
    
    # Log audio data reception (you would process this with your LLM here)
    logger.debug(f"Received audio data: {len(audio_data)} samples at {timestamp}")
    
    # Here you would integrate with your multimodal LLM
    # For now, we'll just send a simple acknowledgment
    
    # Simulate processing delay
    await asyncio.sleep(0.01)
    
    # Send back a processing status
    response = {
        "type": "audio_processed",
        "message": f"Processed {len(audio_data)} audio samples",
        "timestamp": datetime.now().timestamp()
    }
    
    await manager.send_personal_message(json.dumps(response), websocket)

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 