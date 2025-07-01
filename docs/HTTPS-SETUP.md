# 🔒 HTTPS Setup Guide

Your multimodal AI assistant needs HTTPS for microphone access. Here are two simple options:

## 🚀 Option A: Ngrok (Recommended - Real SSL)

**✅ Pros:** Real SSL certificate, no browser warnings, works instantly  
**❌ Cons:** URL changes each time you restart

### Steps:

1. **Get a free ngrok account:**

   - Sign up at: https://ngrok.com/signup
   - Get your auth token from: https://dashboard.ngrok.com/get-started/your-authtoken

2. **Set up ngrok on your AWS server:**

   ```bash
   ssh -i ~/.ssh/multimodal-ai-dev-key.pem ec2-user@54.211.160.83

   # Configure ngrok with your token
   ngrok config add-authtoken YOUR_AUTH_TOKEN_HERE
   ```

3. **Start your app:**

   ```bash
   cd /opt/app/background-multimodal-llm
   docker-compose -f deployment/docker-compose.dev.yml up -d
   ```

4. **Start ngrok tunnel:**

   ```bash
   # In another terminal session
   ngrok http 3000
   ```

5. **Use the HTTPS URL:**
   - You'll get a URL like: `https://abc123.ngrok.io`
   - Share this URL with friends - microphone will work! 🎤

---

## 🔧 Option B: Self-Signed SSL (Permanent URL)

**✅ Pros:** Permanent URL, works offline  
**❌ Cons:** Browser security warning (but still works)

### Steps:

1. **Run the setup script:**

   ```bash
   ./deployment/scripts/add-nginx-ssl.sh
   ```

2. **Update environment variables:**

   ```bash
   # Update your .env file on AWS server to use HTTPS URLs
   REACT_APP_API_URL=https://54.211.160.83/api
   REACT_APP_WS_URL=wss://54.211.160.83/ws
   ```

3. **Restart with SSL:**

   ```bash
   docker-compose -f deployment/docker-compose.dev.yml down
   docker-compose -f deployment/docker-compose.dev.yml up -d
   ```

4. **Access with browser warning:**
   - Visit: `https://54.211.160.83`
   - Click "Advanced" → "Proceed to 54.211.160.83 (unsafe)"
   - Microphone will work despite the warning! 🎤

---

## 🎯 Current Status

- ✅ Ngrok installed on your AWS server
- ✅ Self-signed SSL scripts ready
- ✅ Your app is running on: http://54.211.160.83:3000
- ⚠️ Microphone blocked due to HTTP (needs HTTPS)

**Recommendation:** Try Option A (ngrok) first for the best experience!
