#!/bin/bash

echo "🔒 Setting up HTTPS for your multimodal AI assistant..."

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "📥 Installing ngrok..."
    
    # Download and install ngrok
    curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
    echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
    sudo apt update && sudo apt install ngrok
fi

echo "🔧 Ngrok installed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Sign up for free at: https://ngrok.com/signup"
echo "2. Get your auth token from: https://dashboard.ngrok.com/get-started/your-authtoken" 
echo "3. Run: ngrok config add-authtoken YOUR_TOKEN"
echo "4. Start your app: docker-compose -f docker-compose.dev.yml up -d"
echo "5. In another terminal, run: ngrok http 3000"
echo ""
echo "✅ You'll get an HTTPS URL like: https://abc123.ngrok.io"
echo "🎤 This HTTPS URL will work with microphone access!"
echo ""
echo "💡 Alternative: Use the update-app-for-https.sh script to add nginx with SSL" 