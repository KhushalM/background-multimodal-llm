# Installation Guide

## 🚀 Quick Setup (Recommended)

### Prerequisites
- Python 3.11 or 3.12
- `uv` package manager (install with: `curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Setup Steps

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   uv venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies (choose one method):**

   **🚀 Method 1: Using pyproject.toml (Recommended)**
   ```bash
   # Install core dependencies only
   uv pip install fastapi "uvicorn[standard]" websockets python-multipart httpx openai huggingface-hub google-generativeai transformers langchain langchain-openai langchain-google-genai python-dotenv pydub soundfile pydantic datasets tokenizers numpy pandas pillow requests scipy
   
   # Install PyTorch CPU version
   uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
   ```
   
   **📦 Method 2: Using requirements.txt**
   ```bash
   # Install from requirements file
   uv pip install -r requirements.txt
   
   # Install PyTorch CPU version (if not included)
   uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
   ```
   
   **⚡ Method 3: Regular pip (slower)**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment:**
   ```bash
   cp env.example .env
   # Edit .env and add your API keys
   ```

5. **Test installation:**
   ```bash
   python -c "from main import app; print('✅ Installation successful!')"
   ```

## 📁 File Comparison

### Use `pyproject.toml` (Recommended)
- ✅ **Location:** `backend/pyproject.toml`
- ✅ **Complete:** All dependencies including LangChain, Google AI
- ✅ **Organized:** Core vs optional dependencies  
- ✅ **Modern:** Industry standard for Python projects
- ✅ **Tested:** Successfully installed and working

### Legacy `requirements.txt`
- ⚠️ **Location:** `requirements.txt` (root level)
- ⚠️ **Basic:** Updated but less organized
- ⚠️ **Compatibility:** Kept for older tools

## 🔧 Development

```bash
# Activate environment
source venv/bin/activate

# Run server
python main.py

# Run tests
python test_multimodal.py
```

## 🎯 Summary

**Use `backend/pyproject.toml`** for all development work. It's more complete, better organized, and follows modern Python standards. 