#!/bin/bash

echo "🔒 Adding Nginx with SSL to your development setup..."

# Create nginx directory
mkdir -p nginx ssl

echo "🔑 Generating self-signed SSL certificate..."
# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/nginx.key \
    -out ssl/nginx.crt \
    -subj "/C=US/ST=Dev/L=Dev/O=Dev/CN=54.211.160.83"

echo "📝 Creating simple nginx configuration..."
cat > nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream frontend {
        server frontend:3000;
    }
    
    upstream backend {
        server backend:8000;
    }

    # HTTP redirect to HTTPS
    server {
        listen 80;
        return 301 https://$host$request_uri;
    }

    # HTTPS server
    server {
        listen 443 ssl;
        
        ssl_certificate /etc/ssl/nginx.crt;
        ssl_certificate_key /etc/ssl/nginx.key;
        
        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Backend API  
        location /api/ {
            proxy_pass http://backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket
        location /ws {
            proxy_pass http://backend/ws;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # Health check
        location /health {
            proxy_pass http://backend/health;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

echo "🐳 Adding nginx service to docker-compose.dev.yml..."

# Backup original docker-compose
cp docker-compose.dev.yml docker-compose.dev.yml.backup

# Add nginx service to docker-compose
cat >> docker-compose.dev.yml << 'EOF'

  # HTTPS Nginx Proxy
  nginx:
    image: nginx:alpine
    container_name: multimodal-nginx-dev
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/ssl:ro
    depends_on:
      - frontend
      - backend
    networks:
      - dev-network
    restart: unless-stopped
EOF

echo "✅ SSL setup complete!"
echo ""
echo "🚀 Next steps:"
echo "1. Update your app URLs to use HTTPS:"
echo "   - Frontend: https://54.211.160.83"
echo "   - Backend: https://54.211.160.83/api"
echo "   - WebSocket: wss://54.211.160.83/ws"
echo ""
echo "2. Restart your containers:"
echo "   docker-compose -f docker-compose.dev.yml down"
echo "   docker-compose -f docker-compose.dev.yml up -d"
echo ""
echo "⚠️  Browser will show 'Not Secure' warning for self-signed cert"
echo "   Click 'Advanced' → 'Proceed to 54.211.160.83 (unsafe)'"
echo "   This is normal for development - microphone will work!" 