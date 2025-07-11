FROM python:3.11-slim-bullseye

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies for multimodal AI assistant
RUN apt-get update && apt-get install -y \
    # Build essentials
    build-essential \
    git \
    git-lfs \
    wget \
    curl \
    unzip \
    # Shell and process tools (required for dev container features)
    bash \
    procps \
    # Audio processing for STT/TTS (WebRTC + HuggingFace models)
    ffmpeg \
    portaudio19-dev \
    libasound2-dev \
    libsndfile1-dev \
    # Image processing for screen context analysis
    libjpeg-dev \
    libpng-dev \
    libwebp-dev \
    # Network and security for API calls
    libssl-dev \
    libffi-dev \
    pkg-config \
    ca-certificates \
    # Node.js for React frontend (will install newer version via NodeSource)
    # nodejs \
    # npm \
    # Python development tools
    python3-dev \
    python3-pip \
    # System utilities
    vim \
    nano \
    htop \
    # Sudo for user management
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 18.x (LTS) from NodeSource repository
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install git-lfs for dataset management
RUN git lfs install --system

# Upgrade pip and install essential Python packages including uv for faster package management
RUN pip3 install --no-cache-dir --upgrade \
    pip \
    setuptools \
    wheel \
    uv

# Pre-install core packages for multimodal AI assistant using uv for faster installation
RUN uv pip install --system --no-cache-dir \
    # Backend API framework
    fastapi>=0.104.0 \
    "uvicorn[standard]>=0.24.0" \
    websockets>=12.0 \
    httpx>=0.25.0 \
    # STT/TTS services
    huggingface-hub>=0.19.0 \
    transformers>=4.35.0 \
    torch>=2.2.0 \
    torchaudio>=2.2.0 \
    datasets>=2.14.0 \
    sentencepiece>=0.1.99 \
    # TTS services
    # Cloud AI services (your specific models)
    openai>=1.3.0 \
    google-generativeai>=0.3.0 \
    huggingface-hub>=0.19.0 \
    # Lightweight tokenizers (for API requests only)
    tokenizers>=0.15.0 \
    # Audio processing (only for WebRTC/client-side)
    pydub>=0.25.0 \
    pyaudio>=0.2.11 \
    librosa>=0.10.1 \
    soundfile>=0.12.1 \
    numba>=0.56.0 \
    # Image processing for screen context
    Pillow>=10.0.0 \
    # Data processing
    numpy>=1.24.0 \
    pandas>=2.1.0 \
    # Memory management for conversations
    langchain>=0.1.0 \
    langchain-openai>=0.0.5 \
    langchain-google-genai>=0.0.6 \
    # Environment and validation
    python-dotenv>=1.0.0 \
    pydantic>=2.0.0

# Create workspace directories for cloud-based AI project  
RUN mkdir -p /workspace/{data/{hf_cache,samples},logs} && \
    chmod -R 755 /workspace

# Set up minimal cache for API tokens and responses
ENV HF_HOME=/workspace/data/hf_cache

RUN mkdir -p $HF_HOME

# Create non-root user for development
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && mkdir -p /etc/sudoers.d \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Set ownership of workspace to vscode user
RUN chown -R $USERNAME:$USERNAME /workspace

# Switch to non-root user
USER $USERNAME

# Set working directory
WORKDIR /workspaces/background-multimodal-llm

# Set environment variables
ENV PATH="/home/$USERNAME/.local/bin:$PATH"
ENV PYTHONPATH="/workspaces/background-multimodal-llm"
ENV DEVELOPMENT_MODE=cloud

# Create directories for API keys and configuration
RUN mkdir -p ~/.config

# Expose ports for multimodal AI services (internal container ports)
EXPOSE 3000 8000

# Default command
CMD ["sleep", "infinity"] 