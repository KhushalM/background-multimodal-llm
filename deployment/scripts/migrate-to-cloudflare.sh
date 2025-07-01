#!/bin/bash

echo "🔄 Migrating from ngrok to Cloudflare Tunnel"
echo "============================================"
echo "Domain: back-agent.com"
echo ""

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "📦 Installing cloudflared..."
    
    # Check for package manager to determine OS
    if command -v dpkg &> /dev/null; then
        echo "   Detected Debian/Ubuntu system. Using dpkg."
        wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
        sudo dpkg -i cloudflared-linux-amd64.deb
        rm cloudflared-linux-amd64.deb
    elif command -v rpm &> /dev/null; then
        echo "   Detected RPM-based system (Amazon Linux/CentOS/RHEL). Using rpm."
        wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-x86_64.rpm
        sudo rpm -ivh cloudflared-linux-x86_64.rpm
        rm cloudflared-linux-x86_64.rpm
    else
        echo "   Falling back to direct binary download."
        wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O /tmp/cloudflared
        chmod +x /tmp/cloudflared
        sudo mv /tmp/cloudflared /usr/local/bin/cloudflared
    fi
    
    # Verify installation
    if ! command -v cloudflared &> /dev/null; then
        echo "❌ cloudflared installation failed. Please install it manually from:"
        echo "   https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/"
        exit 1
    fi
    echo "✅ cloudflared installed successfully!"
else
    echo "✅ cloudflared is already installed."
fi

echo ""
echo "🔐 Step 1: Authenticate with Cloudflare"
echo "-------------------------------------"
echo "This will open a browser window. Log in with your Cloudflare account."
echo "Select your domain: back-agent.com when prompted."
echo ""
read -p "Press Enter to continue with authentication..." 

cloudflared tunnel login

if [ $? -ne 0 ]; then
    echo "❌ Authentication failed. Please try again."
    exit 1
fi

echo ""
echo "🚇 Step 2: Create a named tunnel"
echo "-----------------------------"
echo "Creating tunnel: back-agent-tunnel"

TUNNEL_NAME="back-agent-tunnel"
cloudflared tunnel create $TUNNEL_NAME

if [ $? -ne 0 ]; then
    echo "❌ Failed to create tunnel. Please try again."
    exit 1
fi

echo ""
echo "🔗 Step 3: Configure DNS routing"
echo "----------------------------"
echo "Routing back-agent.com to your tunnel..."

cloudflared tunnel route dns $TUNNEL_NAME back-agent.com

if [ $? -ne 0 ]; then
    echo "❌ Failed to configure DNS. Please try again."
    exit 1
fi

echo ""
echo "⚙️ Step 4: Creating tunnel configuration"
echo "------------------------------------"

# Get user's home directory
USER_HOME=$(eval echo ~$USER)
CONFIG_DIR="$USER_HOME/.cloudflared"
CONFIG_FILE="$CONFIG_DIR/config.yml"

# Create config directory if it doesn't exist
mkdir -p $CONFIG_DIR

# Create config file
cat > $CONFIG_FILE << EOF
# Cloudflare Tunnel configuration for back-agent.com
tunnel: $TUNNEL_NAME
credentials-file: $CONFIG_DIR/${TUNNEL_NAME}.json

# Ingress rules
ingress:
  # Frontend
  - hostname: back-agent.com
    service: http://localhost:3000
  
  # Backend API
  - hostname: api.back-agent.com
    service: http://localhost:8000
  
  # Catch-all rule
  - service: http_status:404
EOF

echo "✅ Configuration created at: $CONFIG_FILE"

echo ""
echo "🔄 Step 5: Updating application URLs"
echo "--------------------------------"
echo "Updating all application URLs to use back-agent.com..."

# Make sure the update scripts are executable
chmod +x ./deployment/scripts/quick-update.sh
chmod +x ./deployment/scripts/update-urls.sh

# Run the quick-update script with the new domain
./deployment/scripts/quick-update.sh https://back-agent.com

if [ $? -ne 0 ]; then
    echo "⚠️ Warning: Failed to update application URLs. You may need to update them manually."
else
    echo "✅ Application URLs updated successfully!"
fi

echo ""
echo "🚀 Step 6: Setting up tunnel as a service"
echo "-------------------------------------"

# Create systemd service file
cat > /tmp/cloudflared.service << EOF
[Unit]
Description=Cloudflare Tunnel for back-agent.com
After=network.target

[Service]
User=$USER
ExecStart=/usr/local/bin/cloudflared tunnel run $TUNNEL_NAME
Restart=always
RestartSec=5
StartLimitInterval=60
StartLimitBurst=3

[Install]
WantedBy=multi-user.target
EOF

echo "Would you like to install the tunnel as a system service? (y/n)"
read install_service

if [[ $install_service == "y" || $install_service == "Y" ]]; then
    sudo mv /tmp/cloudflared.service /etc/systemd/system/cloudflared.service
    sudo systemctl daemon-reload
    sudo systemctl enable cloudflared.service
    sudo systemctl start cloudflared.service
    echo "✅ Cloudflare Tunnel service installed and started!"
    echo "   Check status with: sudo systemctl status cloudflared"
else
    echo "📝 To run the tunnel manually:"
    echo "   cloudflared tunnel run $TUNNEL_NAME"
    echo ""
    echo "   To start the tunnel now, run:"
    cloudflared tunnel run $TUNNEL_NAME &
    echo "✅ Tunnel started in background!"
fi

echo ""
echo "🎉 Migration Complete!"
echo "===================="
echo ""
echo "✅ Your app is now available at: https://back-agent.com"
echo "✅ Your API is available at: https://api.back-agent.com"
echo ""
echo "📝 Next steps:"
echo "1. Update any hardcoded ngrok URLs in your code"
echo "2. Update any documentation referring to ngrok"
echo "3. Cancel your ngrok subscription (if applicable)"
echo ""
echo "🔍 To check tunnel status: cloudflared tunnel info $TUNNEL_NAME"
echo "🛑 To stop the tunnel: sudo systemctl stop cloudflared (if installed as service)"
echo "                       or kill the cloudflared process"
echo "" 