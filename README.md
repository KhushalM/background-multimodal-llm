# Background Multimodal LLM

A React frontend application with screen sharing and voice assistant capabilities, built with Vite, Chakra UI, and WebSocket communication.

## Features

- **Screen Sharing**: Capture and share your screen using native Web APIs
- **Voice Assistant**: Real-time audio capture and processing
- **WebSocket Communication**: Real-time bidirectional communication with the backend
- **Modern UI**: Built with Chakra UI v3 for a beautiful, responsive interface
- **TypeScript**: Full type safety throughout the application

## Project Structure

```
background-multimodal-llm/
├── frontend/          # React + Vite frontend
│   ├── src/
│   │   ├── App.tsx    # Main application component
│   │   ├── main.tsx   # Application entry point
│   │   └── index.css  # Global styles
│   └── package.json
├── backend/           # FastAPI WebSocket server
│   ├── main.py        # WebSocket server implementation
│   └── requirements.txt
└── README.md
```

## Getting Started

### Prerequisites

- Node.js (v18 or higher)
- Python 3.11+
- Modern web browser with WebRTC support

### Frontend Setup

1. Navigate to the frontend directory:

   ```bash
   cd frontend
   ```

2. Install dependencies:

   ```bash
   npm install
   ```

3. Start the development server:

   ```bash
   npm run dev
   ```

   The frontend will be available at `http://localhost:3000`

### Backend Setup

1. Navigate to the backend directory:

   ```bash
   cd backend
   ```

2. Create a virtual environment (recommended):

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Start the WebSocket server:

   ```bash
   python main.py
   ```

   The backend will be available at `http://localhost:8000`

## Usage

### Screen Sharing

1. Click the "🖥️ Share Screen" button
2. Select the screen or application window to share
3. The application will begin streaming screen data via WebSocket
4. Click "🛑 Stop Sharing" to end the session

### Voice Assistant

1. Click the "🎙️ Voice Assistant" button
2. Grant microphone permissions when prompted
3. The application will begin capturing and streaming audio data
4. Click "🔇 Stop Voice" to end the session

### WebSocket Communication

The application establishes a WebSocket connection with the backend server to handle:

- Screen sharing events (`screen_share_start`, `screen_share_stop`)
- Voice assistant events (`voice_assistant_start`, `voice_assistant_stop`)
- Real-time audio data streaming (`audio_data`)

## Technical Details

### Frontend Technologies

- **React 18**: Modern React with hooks and functional components
- **TypeScript**: Full type safety and better developer experience
- **Vite**: Fast build tool and development server
- **Chakra UI v3**: Modern, accessible component library
- **Native Web APIs**:
  - `getUserMedia()` for microphone access
  - `getDisplayMedia()` for screen sharing
  - `WebSocket` for real-time communication
  - `AudioContext` for audio processing

### Backend Technologies

- **FastAPI**: Modern, fast web framework for Python
- **WebSockets**: Real-time bidirectional communication
- **Uvicorn**: ASGI server for running the application
- **CORS**: Cross-origin resource sharing for frontend communication

### Browser Permissions

The application requires the following browser permissions:

- **Microphone access**: For voice assistant functionality
- **Screen sharing**: For screen capture capabilities

Make sure to grant these permissions when prompted by your browser.

## API Endpoints

### WebSocket Endpoint

- `ws://localhost:8000/ws` - Main WebSocket endpoint for real-time communication

### HTTP Endpoints

- `GET /` - API status and connection information
- `GET /health` - Health check endpoint

## Development

### Running in Development Mode

1. Start the backend server:

   ```bash
   cd backend && python main.py
   ```

2. In a new terminal, start the frontend:

   ```bash
   cd frontend && npm run dev
   ```

3. Open your browser to `http://localhost:5173`

### Building for Production

1. Build the frontend:

   ```bash
   cd frontend && npm run build
   ```

2. The built files will be in the `frontend/dist` directory

## Current Status - Complete System! 🎉

**Voice Conversation Pipeline with Screen Context**: ✅ **COMPLETED**

- 🎤 **Speech-to-Text (STT)**: Real-time audio transcription using HuggingFace Whisper
- 🧠 **Multimodal AI Brain with Screen Context**: Intelligent responses using Gemini + Vision + LangChain memory
- 🗣️ **Text-to-Speech (TTS)**: Natural speech synthesis using HuggingFace TTS models
- 🖥️ **Screen Understanding**: Integrated visual context analysis using Gemini Vision

**Complete Conversation Flow**:

```
User speaks + Screen capture → Distil-Whisper STT + Screen Analysis → Gemini 2.0 Flash processes with visual context → SpeechT5 TTS → User hears contextual response
```

### What's Working Now

1. ✅ **Real-time Voice Assistant**: Speak to the AI and hear responses
2. ✅ **Screen Context Awareness**: AI can see and understand your screen content
3. ✅ **Conversation Memory**: AI remembers context across the session
4. ✅ **WebSocket Integration**: All services connected through real-time WebSocket
5. ✅ **Multi-user Support**: Separate sessions for concurrent users
6. ✅ **Error Handling**: Robust fallbacks and retry logic

### Quick Start

```bash
# Backend setup
cd backend
pip install -r requirements.txt

# Add API keys to backend/.env
HUGGINGFACE_API_TOKEN=your_hf_token
GEMINI_API_KEY=your_gemini_key

# Start backend
python main.py

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

### Testing the Complete Pipeline

```bash
# Test individual services
python backend/test_stt.py      # Tests Distil-Whisper v3.5
python backend/test_multimodal.py  # Tests Gemini 2.0 Flash with screen context
python backend/test_tts.py      # Tests SpeechT5

# Test complete integration
python backend/test_pipeline.py
```

## System Architecture

The multimodal AI assistant now features a fully integrated architecture:

```
Frontend (React + WebRTC)
    ↓
WebSocket Connection
    ↓
Backend Services:
├── STT Service (Distil-Whisper v3.5)
├── Multimodal Service (Gemini 2.0 Flash + Vision + Memory)
│   ├── Text Processing
│   ├── Screen Analysis
│   ├── Context Integration
│   └── Response Generation
└── TTS Service (SpeechT5)
```

**Key Integration Benefits:**

- Single service handles both text and visual understanding
- Unified context processing for better responses
- Simplified architecture and maintenance
- Reduced latency through integrated processing

## Browser Compatibility

- Chrome/Chromium 88+
- Firefox 88+
- Safari 14+
- Edge 88+

## License

MIT License - see LICENSE file for details
