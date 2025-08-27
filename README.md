# 🎤🖥️ Multimodal AI Assistant

A real-time multimodal AI assistant that combines voice interaction with screen context awareness. Talk to AI while it can see and understand what's on your screen.

## ✨ Features

### 🎯 Core Capabilities

- **🎤 Real-time Voice Chat** - Continuous conversation with VAD (Voice Activity Detection)
- **🖥️ Screen Context Awareness** - AI can see and analyze your screen when relevant
- **🧠 Smart Screen Triggers** - Automatically captures screen based on conversation context
- **⚡ Fast Response Times** - Optimized for real-time interaction
- **🔄 WebSocket Communication** - Low-latency bidirectional communication

### 🤖 AI Models & Services

- **Speech-to-Text**: OpenAI Whisper API
- **Text-to-Speech**: OpenAI TTS API
- **Multimodal AI**: Google Gemini 2.0 Flash Exp
- **Voice Activity Detection**: Silero VAD (via @ricky0123/vad-react)

### 🛠️ Technical Stack

- **Frontend**: React 18 + TypeScript + Vite + Chakra UI
- **Backend**: FastAPI + Python 3.11 + WebSockets
- **Deployment**: Docker + AWS EC2 + GitHub Actions CI/CD
- **Development**: Dev Containers + Hot Reload

## 🚀 Quick Start

### 🐳 Development with Dev Container (Recommended)

```bash
# 1. Open in VS Code with Dev Container extension
# 2. Container auto-setups dependencies
# 3. Start services:

# Terminal 1 - Backend
cd backend && python main.py

# Terminal 2 - Frontend
cd frontend && npm run dev
```

### 💻 Manual Local Development

```bash
# Backend setup
cd backend
uv pip install -r requirements.txt
cp env.example .env  # Configure your API keys
python main.py

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

### 🌐 Access URLs

- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000
- **Health Check**: http://localhost:8000/health

## ⚙️ Configuration

### 🔑 Required API Keys

Copy `backend/env.example` to `backend/.env`:

```bash
# Required for full functionality
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Optional
HUGGINGFACE_API_TOKEN=your_huggingface_token_here
SECRET_KEY=your_secret_key_here
```

### 🎤 Browser Permissions

**Important**: For voice features to work:

- Use **HTTPS** in production (required for microphone access)
- For local development: Chrome/Firefox will ask for microphone permission
- Allow microphone access when prompted

### 🌐 HTTPS URL Setup (Required for Microphone)

**Why HTTPS?** Browsers require HTTPS for microphone access.

**🏆 Best Option: Cloudflare Tunnel with Custom Domain**

```bash
# Run the migration script on your EC2 instance
ssh -i your-key.pem ec2-user@54.211.160.83
cd /opt/app/background-multimodal-llm
./deployment/scripts/migrate-to-cloudflare.sh
```

**Benefits of Cloudflare Tunnel:**

- ✅ Custom domain support (back-agent.com)
- ✅ No bandwidth limits or timeouts
- ✅ Better performance and reliability
- ✅ Enterprise-grade security
- ✅ Free or much cheaper than alternatives ($10/year vs $36-96/year)

**Quick URL Updates:**

```bash
# Update all configurations with new URL
./deployment/scripts/quick-update.sh https://your-domain.com
```

## 🏗️ Project Structure

```
├── backend/              # FastAPI backend
│   ├── main.py          # Main application entry point
│   ├── models/          # AI model integrations
│   ├── services/        # Core services & managers
│   ├── env.example      # Environment configuration template
│   └── requirements.txt # Python dependencies
├── frontend/            # React frontend
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── hooks/       # Custom React hooks
│   │   └── services/    # API service layers
│   └── package.json     # Node dependencies
├── deployment/          # All deployment files
│   ├── docker-compose.dev.yml     # Development deployment
│   ├── scripts/setup-aws-dev.sh   # AWS infrastructure setup
│   └── infrastructure/            # CloudFormation templates
├── docs/               # Documentation
└── .github/workflows/  # CI/CD pipelines
```

## 🔧 Development

### 🛠️ Available Commands

```bash
# Backend
cd backend
python main.py              # Start development server
uv pip install -r requirements.txt  # Install dependencies

# Frontend
cd frontend
npm run dev                  # Start development server
npm run build               # Build for production
npm run preview             # Preview production build

# Deployment
docker-compose -f deployment/docker-compose.dev.yml up -d  # Start with Docker
```

### 🔍 Debugging

```bash
# View logs
docker-compose -f deployment/docker-compose.dev.yml logs -f

# Check specific service
docker-compose -f deployment/docker-compose.dev.yml logs backend
docker-compose -f deployment/docker-compose.dev.yml logs frontend

# Restart services
docker-compose -f deployment/docker-compose.dev.yml restart
```

## 🚀 Deployment

### ☁️ AWS Production Deployment

```bash
# 1. Setup AWS infrastructure
chmod +x deployment/scripts/setup-aws-dev.sh
./deployment/scripts/setup-aws-dev.sh

# 2. Configure GitHub Secrets (for CI/CD)
# Go to: https://github.com/your-repo/settings/secrets/actions
# Add these secrets:
# - DEV_EC2_INSTANCE_IP: Your EC2 public IP
# - DEV_EC2_SSH_PRIVATE_KEY: Your EC2 private key content
# - OPENAI_API_KEY: Your OpenAI API key
# - GEMINI_API_KEY: Your Gemini API key

# 3. Deploy via GitHub Actions
git push origin main  # Triggers automatic deployment
```

### 🔄 Migrating from ngrok to Cloudflare Tunnel

We now use Cloudflare Tunnel instead of ngrok for HTTPS access:

```bash
# Run the migration script
chmod +x deployment/scripts/migrate-to-cloudflare.sh
./deployment/scripts/migrate-to-cloudflare.sh
```

**Benefits of Cloudflare Tunnel vs ngrok:**

- ✅ Custom domain support (back-agent.com)
- ✅ No bandwidth limits or timeouts
- ✅ Better performance and reliability
- ✅ Enterprise-grade security
- ✅ Free or much cheaper than ngrok ($10/year vs $36-96/year)

**After migration:**

- Frontend: https://back-agent.com
- Backend API: https://api.back-agent.com
- WebSockets: wss://api.back-agent.com/ws

### 🔄 Continuous Deployment

- **Push to `main`** → Automatic production deployment
- **Pull requests** → Automatic testing
- **Health checks** → Automatic validation
- **Rollback support** → Safe deployments

### 💰 AWS Costs

- **Development**: ~$5-15/month (free tier eligible)
- **Production**: ~$25-50/month (depends on usage)

## 🎯 Usage Guide

### 🎤 Voice Interaction

1. **Click "Start Voice Assistant"**
2. **Grant microphone permission** when prompted
3. **Start talking** - VAD automatically detects speech
4. **AI responds** with voice and text

### 🖥️ Screen Context

- **Smart Triggers**: AI automatically captures screen when you say things like:
  - "Can you see my screen?"
  - "What's this error?"
  - "Help me with this"
- **Manual Capture**: Click "Share Screen" for continuous sharing
- **Privacy**: Screen capture only when explicitly needed

### 💡 Pro Tips

- **Clear Speech**: Speak clearly for better transcription
- **Context Clues**: Use phrases like "look at this" to trigger screen capture
- **Error Debugging**: Say "what's wrong here?" while viewing errors
- **Natural Conversation**: Talk naturally - the AI understands context

## 🔧 Advanced Configuration

### 🎛️ VAD Sensitivity

Adjust in `frontend/src/hooks/useVoiceAgent.ts`:

```typescript
const vadOptions = {
  positiveSpeechThreshold: 0.8, // Higher = less sensitive
  negativeSpeechThreshold: 0.2, // Lower = less sensitive
  minSpeechFrames: 3, // Minimum frames for speech detection
};
```

### 🖥️ Screen Capture Settings

Configure in `backend/main.py`:

```python
SCREEN_TRIGGER_CONFIDENCE = 0.7  # Confidence threshold for auto-capture
SCREEN_CAPTURE_QUALITY = 0.8     # Image quality (0.1-1.0)
```

## 🐛 Troubleshooting

### Common Issues

**🎤 Microphone not working**

- Ensure HTTPS (required in production)
- Check browser permissions
- Try refreshing the page

**🖥️ Screen sharing not working**

- Use Chrome/Firefox (Safari has limitations)
- Grant screen sharing permission
- Check for browser extensions blocking

**⚡ Slow responses**

- Check your internet connection
- Verify API keys are configured
- Monitor backend logs for errors

**🔌 Connection issues**

- Check WebSocket connection in browser dev tools
- Verify backend is running on port 8000
- Check firewall settings

### 📊 Health Monitoring

- **Health Check**: http://localhost:8000/health
- **Performance**: http://localhost:8000/performance
- **Logs**: `docker-compose logs -f`


