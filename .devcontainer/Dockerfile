FROM python:3.11-slim-bullseye

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies for cloud-based development
RUN apt-get update && apt-get install -y \
    # Build essentials
    build-essential \
    git \
    git-lfs \
    wget \
    curl \
    unzip \
    # Audio processing (lightweight for WebRTC)
    ffmpeg \
    portaudio19-dev \
    libasound2-dev \
    # Image processing (minimal)
    libjpeg-dev \
    libpng-dev \
    # Network and security
    libssl-dev \
    libffi-dev \
    pkg-config \
    # Node.js for frontend development
    nodejs \
    npm \
    # System utilities
    vim \
    nano \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Install git-lfs for dataset management
RUN git lfs install --system

# Upgrade pip and install essential Python packages
RUN pip3 install --no-cache-dir --upgrade \
    pip \
    setuptools \
    wheel

# Install lightweight ML libraries (CPU-only)
RUN pip3 install --no-cache-dir \
    torch \
    torchvision \
    torchaudio \
    --index-url https://download.pytorch.org/whl/cpu

# Create workspace directories
RUN mkdir -p /workspace/{data,logs,frontend,backend,notebooks} && \
    chmod -R 755 /workspace

# Create cache directories for cloud services
ENV HF_DATASETS_CACHE=/workspace/data/hf_cache
ENV TRANSFORMERS_CACHE=/workspace/data/transformers_cache

RUN mkdir -p $HF_DATASETS_CACHE $TRANSFORMERS_CACHE

# Create non-root user for development
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
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
ENV JUPYTER_ENABLE_LAB=yes
ENV DEVELOPMENT_MODE=cloud

# Pre-install core packages for development
RUN pip3 install --user --no-cache-dir \
    fastapi \
    uvicorn \
    websockets \
    openai \
    huggingface-hub \
    jupyter \
    jupyterlab \
    streamlit

# Set up Jupyter configuration
RUN jupyter lab --generate-config && \
    echo "c.ServerApp.ip = '0.0.0.0'" >> ~/.jupyter/jupyter_lab_config.py && \
    echo "c.ServerApp.allow_root = True" >> ~/.jupyter/jupyter_lab_config.py && \
    echo "c.ServerApp.open_browser = False" >> ~/.jupyter/jupyter_lab_config.py && \
    echo "c.ServerApp.token = ''" >> ~/.jupyter/jupyter_lab_config.py && \
    echo "c.ServerApp.password = ''" >> ~/.jupyter/jupyter_lab_config.py

# Create AWS credentials directory (optional)
RUN mkdir -p ~/.aws

# Expose ports for services
EXPOSE 3000 8000 8888 8501

# Default command
CMD ["sleep", "infinity"] 