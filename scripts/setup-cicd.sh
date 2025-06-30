#!/bin/bash

echo "🚀 Setting up automatic CI/CD deployment..."
echo ""

# Get current public IP
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "54.211.160.83")

echo "📋 You need to add these GitHub Secrets for automatic deployment:"
echo ""
echo "Go to: https://github.com/KhushalM/background-multimodal-llm/settings/secrets/actions"
echo "Click 'New repository secret' for each of these:"
echo ""

echo "1. DEV_EC2_INSTANCE_IP"
echo "   Value: $PUBLIC_IP"
echo ""

echo "2. DEV_EC2_SSH_PRIVATE_KEY"
echo "   Value: (your private key content)"
echo "   To get the private key:"
echo "   cat ~/.ssh/multimodal-ai-dev-key.pem"
echo "   Copy the ENTIRE content including -----BEGIN and -----END lines"
echo ""

echo "3. OPENAI_KEY (if you have one)"
echo "   Value: your-openai-api-key"
echo ""

echo "4. GEMINI_API_KEY (if you have one)"
echo "   Value: your-gemini-api-key"
echo ""

echo "5. HUGGINGFACE_API_TOKEN (optional)"
echo "   Value: your-huggingface-token"
echo ""

echo "✅ After adding these secrets:"
echo "   1. Push any code change to GitHub"
echo "   2. GitHub Actions will automatically:"
echo "      - Run tests"
echo "      - Deploy to your AWS server"
echo "      - Restart containers"
echo "      - Run health checks"
echo ""

echo "🎯 No more manual pulling/rebuilding needed!"
echo ""

echo "🔗 Monitor deployments at:"
echo "   https://github.com/KhushalM/background-multimodal-llm/actions" 