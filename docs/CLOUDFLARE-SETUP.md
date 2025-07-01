# 🔒 HTTPS Setup with Cloudflare Tunnel

Your multimodal AI assistant needs HTTPS for microphone access. We use Cloudflare Tunnel for secure, reliable HTTPS.

## 🚀 Option A: Custom Domain (Recommended)

**✅ Pros:** Professional URL, permanent, full control, enterprise-grade security  
**✅ Cost:** Domain (~$10/year) + FREE Cloudflare Tunnel

### Steps:

1. **Register a domain with Cloudflare:**

   - Sign up at: https://dash.cloudflare.com/sign-up
   - Register a domain (~$10/year) or transfer an existing one

2. **Run the migration script on your EC2 instance:**

   ```bash
   ssh -i your-key.pem ec2-user@54.211.160.83
   cd /opt/app/background-multimodal-llm
   ./deployment/scripts/migrate-to-cloudflare.sh
   ```

3. **Follow the prompts to:**

   - Authenticate with Cloudflare
   - Create a tunnel for your domain
   - Configure DNS records
   - Set up the tunnel as a service

4. **Access your app:**
   - Frontend: https://yourdomain.com
   - Backend API: https://api.yourdomain.com
   - WebSockets: wss://api.yourdomain.com/ws

## 🔄 Option B: Free Cloudflare URL (No Domain Required)

**✅ Pros:** Completely FREE, no domain purchase needed, secure HTTPS  
**❌ Cons:** Less professional URL

### Steps:

1. **Install cloudflared on your EC2 instance:**

   ```bash
   wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
   sudo dpkg -i cloudflared-linux-amd64.deb
   ```

2. **Start a quick tunnel:**

   ```bash
   cloudflared tunnel --url http://localhost:3000
   ```

3. **Update your app configuration:**

   ```bash
   ./deployment/scripts/quick-update.sh https://your-random-url.trycloudflare.com
   ```

4. **Access your app:**
   - Your app will be available at the provided trycloudflare.com URL
   - Microphone and screen sharing will work!

## 🔧 Advanced Configuration

### Setting Up Subdomain Routing

To route different services to different subdomains:

1. **Create a config file:**

   ```yaml
   # ~/.cloudflared/config.yml
   tunnel: your-tunnel-id
   credentials-file: /home/ec2-user/.cloudflared/your-tunnel-id.json

   ingress:
     - hostname: yourdomain.com
       service: http://localhost:3000
     - hostname: api.yourdomain.com
       service: http://localhost:8000
     - service: http_status:404
   ```

2. **Update DNS records:**

   ```bash
   cloudflared tunnel route dns your-tunnel-name yourdomain.com
   cloudflared tunnel route dns your-tunnel-name api.yourdomain.com
   ```

3. **Run the tunnel with the config:**
   ```bash
   cloudflared tunnel run your-tunnel-name
   ```

### Running as a System Service

For production, run as a systemd service:

```bash
sudo tee /etc/systemd/system/cloudflared.service << EOF
[Unit]
Description=Cloudflare Tunnel
After=network.target

[Service]
User=ec2-user
ExecStart=/usr/local/bin/cloudflared tunnel run your-tunnel-name
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

## 🎯 Benefits Over Ngrok

- ✅ No bandwidth limits or timeouts
- ✅ No changing URLs (with custom domain)
- ✅ Better performance and reliability
- ✅ Enterprise-grade security
- ✅ Free or much cheaper ($10/year vs $36-96/year)
