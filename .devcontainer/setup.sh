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
mkdir -p {
    frontend/{src/{components,pages,hooks,utils},public},
    backend/{api,services,utils},
    data/{cache,samples},
    notebooks,
    scripts
}

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

# Simple React package.json
cat > frontend/package.json << 'EOF'
{
  "name": "ai-assistant-frontend",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build"
  },
  "proxy": "http://localhost:8000"
}
EOF

# Set up Jupyter
print_info "Configuring Jupyter Lab..."
jupyter lab --generate-config --allow-root 2>/dev/null || true

# Create a simple getting started notebook
cat > notebooks/getting_started.ipynb << 'EOF'
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Personal AI Assistant - Getting Started\n",
    "\n",
    "Quick setup and testing of your cloud-based AI assistant."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import os\n",
    "from dotenv import load_dotenv\n",
    "\n",
    "load_dotenv()\n",
    "\n",
    "print(\"API Keys Status:\")\n",
    "print(f\"OpenAI: {'✅' if os.getenv('OPENAI_API_KEY') else '❌'}\")\n",
    "print(f\"HuggingFace: {'✅' if os.getenv('HUGGINGFACE_API_TOKEN') else '❌'}\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Test OpenAI API\n",
    "try:\n",
    "    import openai\n",
    "    client = openai.OpenAI()\n",
    "    response = client.chat.completions.create(\n",
    "        model=\"gpt-3.5-turbo\",\n",
    "        messages=[{\"role\": \"user\", \"content\": \"Hello!\"}],\n",
    "        max_tokens=20\n",
    "    )\n",
    "    print(\"OpenAI Response:\", response.choices[0].message.content)\n",
    "except Exception as e:\n",
    "    print(f\"OpenAI Error: {e}\")"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
EOF

# Install frontend dependencies if npm is available
if command -v npm &> /dev/null; then
    print_info "Installing frontend dependencies..."
    cd frontend && npm install && cd ..
    print_status "Frontend dependencies installed"
fi

print_status "Setup complete!"
echo ""
print_info "🚀 Quick Start:"
echo "  1. Copy .env.example to .env and add your API keys"
echo "  2. Start backend: python backend/main.py"
echo "  3. Start frontend: cd frontend && npm start"
echo "  4. Open Jupyter: jupyter lab"
echo "  5. Try Streamlit: streamlit run your_app.py"
echo ""
print_info "📂 Simple Structure:"
echo "  frontend/: React app"
echo "  backend/: FastAPI server"
echo "  notebooks/: Jupyter experiments"
echo "  data/: Local data storage"
echo ""
print_status "Ready to build your AI assistant! 🤖" 