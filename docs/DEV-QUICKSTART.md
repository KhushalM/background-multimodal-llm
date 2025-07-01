# 🚀 AWS Development Deployment - Quick Start

**Status**: ✅ **WORKING DEPLOYMENT** - Successfully tested!

## 📋 **What You Have**

Your AWS development environment is now **LIVE** and running:

- **✅ EC2 Instance**: `i-00f5ed5f6b91645c6` (running)
- **✅ Public IP**: `54.211.160.83`
- **✅ Instance Type**: t3.micro (free tier eligible)
- **✅ Storage**: 20GB EBS volume
- **✅ Cost**: ~$5-15/month (free for 12 months if new AWS account)

## 🔗 **Access Your Environment**

### **SSH to Your Server**

```bash
ssh -i ~/.ssh/multimodal-ai-dev-key.pem ec2-user@54.211.160.83
```

### **Application URLs** (after deployment)

- **Frontend**: http://54.211.160.83:3000
- **Backend**: http://54.211.160.83:8000

## 🚀 **Deploy Your Application**

1. **SSH to your server**:

```bash
ssh -i ~/.ssh/multimodal-ai-dev-key.pem ec2-user@54.211.160.83
```

2. **Clone your repository**:

```bash
cd /opt/app
sudo git clone https://github.com/KhushalM/background-multimodal-llm.git .
sudo chown -R ec2-user:ec2-user /opt/app
```

3. **Update environment variables**:

```bash
cat > .env << 'EOF'
NODE_ENV=development
REACT_APP_API_URL=http://54.211.160.83:8000
REACT_APP_WS_URL=ws://54.211.160.83:8000
DATABASE_URL=sqlite:///app/dev_database.db
OPENAI_API_KEY=your_new_openai_key_here
GEMINI_API_KEY=your_new_gemini_key_here
HUGGINGFACE_API_TOKEN=placeholder
SECRET_KEY=dev-secret-key
CORS_ORIGINS=http://54.211.160.83:3000,http://54.211.160.83:8000
EOF
```

4. **Start your application**:

```bash
docker-compose -f deployment/docker-compose.dev.yml up -d --build
```

5. **Check if it's running**:

```bash
docker-compose -f deployment/docker-compose.dev.yml ps
curl http://localhost:8000/health
```

## 🔧 **What Made This Work**

### **Simplified Architecture**

- ✅ **No IAM roles** (avoided S3 ARN reference errors)
- ✅ **No S3 bucket** (not essential for basic development)
- ✅ **Basic networking** (VPC + subnet + security group)
- ✅ **Single EC2 instance** with Elastic IP

### **Key Components**

```
✅ VPC (10.0.0.0/16)
✅ Public Subnet (10.0.1.0/24)
✅ Internet Gateway + Route Table
✅ Security Group (ports 22, 80, 3000, 8000)
✅ EC2 t3.micro + Elastic IP
✅ 20GB EBS storage
```

## 🔄 **Auto-Deployment with GitHub Actions**

Your repository has CI/CD configured! When you push to `master` branch:

1. **Tests run automatically**
2. **Code deploys to EC2**
3. **Services restart**

To set this up, add these GitHub Secrets:

- `DEV_EC2_INSTANCE_IP`: `54.211.160.83`
- `DEV_EC2_SSH_PRIVATE_KEY`: (contents of `~/.ssh/multimodal-ai-dev-key.pem`)

## 🛠️ **Management Commands**

### **On Your Local Machine**

```bash
# Check instance status
aws ec2 describe-instances --instance-ids i-00f5ed5f6b91645c6 --region us-east-1

# Stop instance (save money)
aws ec2 stop-instances --instance-ids i-00f5ed5f6b91645c6 --region us-east-1

# Start instance
aws ec2 start-instances --instance-ids i-00f5ed5f6b91645c6 --region us-east-1
```

### **On Your EC2 Server**

```bash
# View logs
docker-compose -f deployment/docker-compose.dev.yml logs -f

# Restart services
docker-compose -f deployment/docker-compose.dev.yml restart

# Stop everything
docker-compose -f deployment/docker-compose.dev.yml down

# Start everything
docker-compose -f deployment/docker-compose.dev.yml up -d --build
```

## 💰 **Cost Control**

- **Free Tier**: 750 hours/month free for t3.micro (12 months)
- **Stop when not using**: `aws ec2 stop-instances --instance-ids i-00f5ed5f6b91645c6`
- **Monitor costs**: AWS Billing Dashboard

## 🚨 **Troubleshooting**

### **Can't SSH?**

```bash
# Check security group allows port 22
# Verify key permissions: chmod 400 ~/.ssh/multimodal-ai-dev-key.pem
```

### **Application not loading?**

```bash
# SSH to server and check:
docker ps                                    # Are containers running?
docker-compose -f deployment/docker-compose.dev.yml logs  # Check logs
curl http://localhost:8000/health            # Backend health
```

### **Need to redeploy?**

```bash
# SSH to server:
cd /opt/app
git pull origin master
docker-compose -f deployment/docker-compose.dev.yml up -d --build
```

## 🎯 **Next Steps**

1. **Deploy your app** using the steps above
2. **Test the frontend/backend**
3. **Set up GitHub Actions** for auto-deployment
4. **Monitor costs** in AWS console

Your development environment is ready! 🎉
