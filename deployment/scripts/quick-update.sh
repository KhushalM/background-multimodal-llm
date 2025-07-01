#!/bin/bash

echo "⚡ Quick Update & Restart - Update URLs and restart app in one command!"
echo ""

# Check if URL is provided
if [ $# -eq 0 ]; then
    echo "❌ Error: No HTTPS URL provided"
    echo ""
    echo "Usage: $0 <new-https-url>"
    echo "Example: $0 https://back-agent.com"
    echo ""
    echo "This will:"
    echo "  1. Update all configuration files"
    echo "  2. Stop current containers"
    echo "  3. Restart with new URLs"
    echo "  4. Run health checks"
    exit 1
fi

NEW_URL="$1"

# Step 1: Update URLs
echo "🔗 Step 1: Updating URLs..."
./deployment/scripts/update-urls.sh "$NEW_URL"

if [ $? -ne 0 ]; then
    echo "❌ URL update failed. Aborting."
    exit 1
fi

echo ""
echo "🔄 Step 2: Restarting application..."

# Step 2: Stop existing containers
echo "🛑 Stopping containers..."
docker-compose -f deployment/docker-compose.dev.yml down

# Step 3: Start with new configuration
echo "🚀 Starting with new URLs..."
docker-compose -f deployment/docker-compose.dev.yml up -d --build

# Step 4: Wait and health check
echo "⏳ Waiting for services to start..."
sleep 15

# Step 5: Health checks
echo "🏥 Running health checks..."
BACKEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "$NEW_URL/health" 2>/dev/null)
FRONTEND_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "$NEW_URL" 2>/dev/null)

echo ""
echo "📊 Health Check Results:"
if [ "$BACKEND_HEALTH" = "200" ]; then
    echo "   ✅ Backend: Healthy ($NEW_URL/health)"
else
    echo "   ⚠️  Backend: Not responding (HTTP $BACKEND_HEALTH)"
fi

if [ "$FRONTEND_CHECK" = "200" ]; then
    echo "   ✅ Frontend: Accessible ($NEW_URL)"
else
    echo "   ⚠️  Frontend: Not responding (HTTP $FRONTEND_CHECK)"
fi

echo ""
echo "🎉 Quick update completed!"
echo ""
echo "🔗 Your app is now running at:"
echo "   Frontend: $NEW_URL"
echo "   Backend:  $NEW_URL/health"
echo "   WebSocket: ${NEW_URL/https:/wss:}/ws"
echo ""
echo "🎤 Remember: Microphone and screen sharing now work with HTTPS!"
echo ""
echo "📊 View logs: docker-compose -f deployment/docker-compose.dev.yml logs -f" 