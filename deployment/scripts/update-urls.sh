#!/bin/bash

echo "🔗 URL Updater - Update all URLs in one command!"
echo ""

# Function to show usage
show_usage() {
    echo "Usage: $0 <new-https-url>"
echo ""
echo "Examples:"
echo "  $0 https://api.back-agent.com"
echo "  $0 https://abc123.trycloudflare.com"
    echo ""
    echo "This will update URLs in:"
    echo "  - deployment/docker-compose.dev.yml"
    echo "  - frontend/vite.config.ts"
    echo "  - .github/workflows/deploy-dev.yml (if needed)"
    echo ""
}

# Check if URL is provided
if [ $# -eq 0 ]; then
    echo "❌ Error: No HTTPS URL provided"
    show_usage
    exit 1
fi

NEW_URL="$1"

# Validate URL format
if [[ ! "$NEW_URL" =~ ^https:// ]]; then
    echo "❌ Error: Invalid URL format"
    echo "   URL must start with https://"
    echo "   Got: $NEW_URL"
    exit 1
fi

# Extract base URL and create variants
BASE_URL="$NEW_URL"
WS_URL="${NEW_URL/https:/wss:}"

echo "🎯 Updating URLs:"
echo "   HTTP/HTTPS: $BASE_URL"
echo "   WebSocket:  $WS_URL"
echo ""

# Backup files before making changes
echo "💾 Creating backups..."
cp deployment/docker-compose.dev.yml deployment/docker-compose.dev.yml.backup
cp frontend/vite.config.ts frontend/vite.config.ts.backup
echo "   ✅ Backups created (.backup files)"
echo ""

# Update docker-compose.dev.yml
echo "🔧 Updating deployment/docker-compose.dev.yml..."

# Update frontend environment variables
sed -i "s|REACT_APP_API_URL=https://[^\"]*|REACT_APP_API_URL=$BASE_URL|g" deployment/docker-compose.dev.yml
sed -i "s|REACT_APP_WS_URL=wss://[^\"]*|REACT_APP_WS_URL=$WS_URL|g" deployment/docker-compose.dev.yml
sed -i "s|VITE_REACT_APP_API_URL=https://[^\"]*|VITE_REACT_APP_API_URL=$BASE_URL|g" deployment/docker-compose.dev.yml
sed -i "s|VITE_REACT_APP_WS_URL=wss://[^\"]*|VITE_REACT_APP_WS_URL=$WS_URL|g" deployment/docker-compose.dev.yml

# Update CORS origins (keep existing + add new)
sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=http://54.211.160.83:3000,http://54.211.160.83:8000,$BASE_URL,http://localhost:3000,http://127.0.0.1:3000|g" deployment/docker-compose.dev.yml

echo "   ✅ Updated docker-compose.dev.yml"

# Update frontend/vite.config.ts
echo "🔧 Updating frontend/vite.config.ts..."

# Update proxy targets
sed -i "s|target: 'https://[^']*'|target: '$BASE_URL'|g" frontend/vite.config.ts
sed -i "s|target: 'wss://[^']*'|target: '$WS_URL'|g" frontend/vite.config.ts

echo "   ✅ Updated vite.config.ts"

# Check if GitHub Actions workflow needs updating
if [ -f ".github/workflows/deploy-dev.yml" ]; then
    echo "🔧 Checking GitHub Actions workflow..."
    if grep -q "ngrok" .github/workflows/deploy-dev.yml; then
        echo "   ⚠️  Found ngrok references in GitHub Actions"
        echo "   📝 You may need to manually update .github/workflows/deploy-dev.yml"
    else
        echo "   ✅ No ngrok references found in GitHub Actions"
    fi
fi

echo ""
echo "🎉 URL update completed!"
echo ""
echo "📋 Summary of changes:"
echo "   Frontend API URL: $BASE_URL"
echo "   WebSocket URL:    $WS_URL"
echo "   CORS Origins:     Updated to include new URL"
echo ""
echo "🚀 Next steps:"
echo "   1. Make sure your Cloudflare tunnel is running: cloudflared tunnel run back-agent-tunnel"
echo "   2. Restart your application:"
echo "      docker-compose -f deployment/docker-compose.dev.yml down"
echo "      docker-compose -f deployment/docker-compose.dev.yml up -d"
echo ""
echo "🔄 To revert changes:"
echo "   mv deployment/docker-compose.dev.yml.backup deployment/docker-compose.dev.yml"
echo "   mv frontend/vite.config.ts.backup frontend/vite.config.ts"
echo ""
echo "💡 Pro tip: Bookmark this command for quick updates!"
echo "   ./deployment/scripts/update-urls.sh https://back-agent.com" 