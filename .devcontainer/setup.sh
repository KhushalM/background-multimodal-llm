#!/bin/bash

echo "🚀 Setting up Personal Multimodal AI Assistant..."
echo "   Lightweight cloud development for MacBook M1 Pro"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check development environment
print_info "Checking development environment..."
echo "Platform: $(uname -m)"
echo "Python: $(python --version 2>/dev/null || echo 'Not available')"
echo "Node.js: $(node --version 2>/dev/null || echo 'Not available')"

# Install Python dependencies
print_info "Installing Python dependencies..."
pip install --upgrade pip setuptools wheel

if pip install -r requirements.txt; then
    print_status "Dependencies installed successfully"
else
    print_warning "Some dependencies may have failed. Check output above."
fi

# Create simple project structure
print_info "Creating project structure..."
mkdir -p frontend/src/components \
         frontend/src/pages \
         frontend/src/hooks \
         frontend/src/utils \
         frontend/public \

         backend/services \
         backend/utils \
         


print_status "Project structure created"

# Create basic configuration files
print_info "Creating configuration files..."

# Simple FastAPI backend
cat > backend/main.py << 'EOF'
"""
Personal Multimodal AI Assistant Backend
Simple FastAPI server with cloud AI integration
"""
import os
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Personal AI Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Personal AI Assistant API", "status": "ready"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "huggingface": bool(os.getenv("HUGGINGFACE_API_TOKEN"))
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except:
        pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF

# Simple environment template
cat > .env.example << 'EOF'
# API Keys (add your own)
OPENAI_API_KEY=your_openai_key_here
HUGGINGFACE_API_TOKEN=your_hf_token_here

# Optional: AWS (uncomment if needed)
# AWS_ACCESS_KEY_ID=your_aws_key
# AWS_SECRET_ACCESS_KEY=your_aws_secret

# Development
DEBUG=true
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
EOF

# Note: Frontend package.json already exists with Vite configuration
# No need to overwrite it

# Install frontend dependencies if npm is available
if command -v npm &> /dev/null; then
    print_info "Installing frontend dependencies..."
    if [ -f "frontend/package.json" ]; then
        cd frontend && npm install && cd ..
        print_status "Frontend dependencies installed"
    else
        print_warning "Frontend package.json not found - skipping npm install"
    fi
fi

print_status "Setup complete!"
echo ""
print_info "🚀 Quick Start:"
echo "  1. Copy .env.example to .env and add your API keys"
echo "  2. Start backend: python backend/main.py"
echo "  3. Start frontend: cd frontend && npm run dev"
echo "  4. Try Streamlit: streamlit run your_app.py"
echo ""
print_info "🌐 Access URLs:"
echo "  Frontend (Vite): http://localhost:3000"
echo "  Backend (FastAPI): http://localhost:8000"
echo ""
print_info "📂 Project Structure:"
echo "  frontend/: React + TypeScript + Vite + Chakra UI"
echo "  backend/: FastAPI server with multimodal AI"
echo "  data/: Local data storage"
echo ""
print_info "💡 Development Tips:"
echo "  • Frontend: Always run 'npm run dev' from frontend/ directory"
echo "  • Backend: Run 'python main.py' from backend/ directory"
echo "  • Use 'npm run build' to create production build"
echo ""
print_status "Ready to build your AI assistant! 🤖" 