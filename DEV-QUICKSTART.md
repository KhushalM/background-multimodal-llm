# 🚀 Development Quick Start Guide

Deploy your **Multimodal AI Assistant** to AWS for development in under 20 minutes - **for just $5-15/month!**

## ⚡ **Super Quick Setup** (One Command)

```bash
# Run the development setup script
chmod +x scripts/setup-aws-dev.sh
./scripts/setup-aws-dev.sh
```

**What this creates:**

- ✅ **t3.micro EC2 instance** (free tier eligible!)
- ✅ **SQLite database** (no PostgreSQL complexity)
- ✅ **Simple networking** (no CloudFront/Route53)
- ✅ **CI/CD with GitHub Actions**
- ✅ **Hot reloading** for development

## 📋 **Prerequisites** (2 minutes)

1. **AWS Account** + **AWS CLI**:

   ```bash
   # Install AWS CLI
   brew install awscli   # macOS
   # OR
   sudo apt install awscli   # Ubuntu

   # Configure it
   aws configure
   ```

2. **That's it!** (jq is optional but helpful)

## 🎯 **Development vs Production**

| Feature        | Development          | Production       |
| -------------- | -------------------- | ---------------- |
| **Cost**       | ~$5-15/month         | ~$20-40/month    |
| **Instance**   | t3.micro (free tier) | t3.small         |
| **Database**   | SQLite (simple)      | PostgreSQL       |
| **Storage**    | Basic S3             | S3 + CloudFront  |
| **SSL**        | Not needed           | Full SSL setup   |
| **Complexity** | Very simple          | Production-ready |

## 🚀 **Step-by-Step Deployment**

### **Step 1: Create AWS Infrastructure** (5 minutes)

```bash
# Run the dev setup script
./scripts/setup-aws-dev.sh
```

**It will ask you:**

- GitHub repository URL
- AWS region (default: us-east-1)
- API keys (optional - add later)

### **Step 2: Configure GitHub Secrets** (2 minutes)

1. Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions**
2. Add secrets from the generated `github-dev-secrets.txt` file:
   ```
   DEV_EC2_INSTANCE_IP=your-ec2-ip
   DEV_EC2_SSH_PRIVATE_KEY=contents-of-your-pem-file
   ```

### **Step 3: Deploy Your Code** (3 minutes)

```bash
# Push to main branch to trigger auto-deployment
git add .
git commit -m "feat: setup development deployment"
git push origin main
```

**OR manually deploy:**

```bash
# SSH to your EC2 instance
ssh -i ~/.ssh/multimodal-ai-dev-key.pem ec2-user@YOUR_EC2_IP

# Clone and start your app
git clone YOUR_GITHUB_REPO /opt/app
cd /opt/app
docker-compose -f docker-compose.dev.yml up -d
```

### **Step 4: Access Your App** (1 minute)

- **Frontend**: `http://your-ec2-ip:3000`
- **Backend**: `http://your-ec2-ip:8000`
- **Health Check**: `http://your-ec2-ip:8000/health`

## 🎉 **You're Live!**

Your development environment is now running with:

- **Hot reloading** - changes update automatically
- **CI/CD** - push code → automatic deployment
- **Cost effective** - free tier eligible

## 💡 **Essential Dev Commands**

```bash
# SSH to your development server
ssh -i ~/.ssh/multimodal-ai-dev-key.pem ec2-user@YOUR_EC2_IP

# View live logs
docker-compose -f docker-compose.dev.yml logs -f

# Restart everything
docker-compose -f docker-compose.dev.yml restart

# Stop everything (save money when not using)
docker-compose -f docker-compose.dev.yml down

# Start everything
docker-compose -f docker-compose.dev.yml up -d
```

## 🔧 **Add API Keys Later**

```bash
# SSH to your server
ssh -i ~/.ssh/multimodal-ai-dev-key.pem ec2-user@YOUR_EC2_IP

# Edit environment file
nano /opt/app/.env

# Update these lines:
OPENAI_API_KEY=sk-your-real-key
GEMINI_API_KEY=your-real-gemini-key
HUGGINGFACE_API_TOKEN=hf_your-real-token

# Restart to use new keys
cd /opt/app
docker-compose -f docker-compose.dev.yml restart backend
```

## 💰 **Development Costs**

**~$5-15/month total:**

- **EC2 t3.micro**: $0-8/month (FREE for first 12 months!)
- **S3 storage**: $1-3/month
- **Data transfer**: $1-3/month
- **Other services**: $1-2/month

**💡 Save even more:**

```bash
# Stop EC2 when not using (pay only for storage)
aws ec2 stop-instances --instance-ids YOUR_INSTANCE_ID

# Start when needed
aws ec2 start-instances --instance-ids YOUR_INSTANCE_ID
```

## 🛠️ **Quick Troubleshooting**

### **Can't SSH?**

```bash
# Check security group
aws ec2 describe-security-groups --filters "Name=group-name,Values=*multimodal-ai-dev*"

# Fix key permissions
chmod 400 ~/.ssh/multimodal-ai-dev-key.pem
```

### **App not starting?**

```bash
# Check logs
docker-compose -f docker-compose.dev.yml logs

# Restart containers
docker-compose -f docker-compose.dev.yml restart

# Check disk space
df -h
```

### **GitHub Actions failing?**

1. Check secrets are added correctly
2. Verify SSH key is pasted completely
3. Make sure EC2 instance is running

## 🔄 **CI/CD Workflow**

**Automatic deployment on:**

- ✅ Push to `main` branch
- ✅ Push to `develop` branch
- ✅ Pull requests (testing only)

**What happens:**

1. **Tests run** (if you have any)
2. **Code gets pulled** to EC2
3. **Containers restart** with new code
4. **Health checks** verify everything works

## 📊 **Monitoring Your Dev Environment**

```bash
# Check container status
docker ps

# Monitor resource usage
docker stats

# Check available space
df -h

# View system load
top
```

## 🚀 **When Ready for Production**

1. **Use the production setup**: `./scripts/setup-aws.sh`
2. **Add a domain name** and SSL certificates
3. **Switch to PostgreSQL** database
4. **Enable CloudFront** for global distribution
5. **Set up monitoring** and backups

## 📞 **Need Help?**

**Check these files:**

- `dev-deployment-summary.md` - Complete setup details
- `github-dev-secrets.txt` - GitHub configuration
- AWS CloudFormation console - Infrastructure status

**Quick fixes:**

```bash
# Restart everything
docker-compose -f docker-compose.dev.yml restart

# Check logs
docker-compose -f docker-compose.dev.yml logs -f

# Update code
git pull && docker-compose -f docker-compose.dev.yml restart
```

---

🎯 **Perfect for development!** You now have a cost-effective, CI/CD-enabled development environment that's perfect for building and testing your multimodal AI assistant.

**Total setup time: ~15-20 minutes** ⏱️  
**Monthly cost: ~$5-15** 💰  
**Features: Full CI/CD + Hot reloading** 🚀
