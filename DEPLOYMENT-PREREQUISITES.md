# 📋 Development Deployment Prerequisites

Complete these steps before running the development deployment.

## ✅ **1. AWS Account & Billing** (Required)

### Create AWS Account

1. Go to [aws.amazon.com](https://aws.amazon.com)
2. Click "Create an AWS Account"
3. Follow the signup process
4. **Add a credit card** (required even for free tier)
5. **Verify your phone number**

### Check Free Tier Eligibility

- **New accounts get 12 months free tier**
- t3.micro instances are free (750 hours/month)
- Check status: [AWS Free Tier Dashboard](https://console.aws.amazon.com/billing/home#/freetier)

### Set Billing Alerts (Recommended)

```bash
# After AWS CLI setup, create a billing alert
aws budgets create-budget --account-id YOUR_ACCOUNT_ID --budget '{
  "BudgetName": "DevDeploymentBudget",
  "BudgetLimit": {
    "Amount": "20",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}'
```

## ✅ **2. Install AWS CLI** (Required)

### macOS

```bash
# Using Homebrew (recommended)
brew install awscli

# Verify installation
aws --version
```

### Ubuntu/Debian Linux

```bash
# Using apt
sudo apt update
sudo apt install awscli

# Verify installation
aws --version
```

### Windows

```bash
# Download and install from:
# https://aws.amazon.com/cli/
# Or use Windows Subsystem for Linux (WSL)
```

### Alternative: Install AWS CLI v2 (Latest)

```bash
# macOS/Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

## ✅ **3. Create AWS IAM User** (Required)

### Why Not Use Root Account?

- Root account has unlimited permissions (dangerous)
- Best practice: Create IAM user with specific permissions

### Create IAM User with Deployment Permissions

1. **Go to AWS Console** → IAM → Users → "Create User"
2. **Username**: `multimodal-dev-deployer`
3. **Access Type**: ✅ "Programmatic access"
4. **Permissions**: Attach these policies:
   - `PowerUserAccess` (easiest for development)
   - OR create custom policy (more secure):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ec2:*", "cloudformation:*", "iam:*", "s3:*"],
      "Resource": "*"
    }
  ]
}
```

5. **Save the credentials**:
   - Access Key ID: `AKIA...`
   - Secret Access Key: `...` (only shown once!)

## ✅ **4. Configure AWS CLI** (Required)

### Run AWS Configure

```bash
aws configure
```

### Enter Your Information

```
AWS Access Key ID [None]: AKIA... (from step 3)
AWS Secret Access Key [None]: ... (from step 3)
Default region name [None]: us-east-1
Default output format [None]: json
```

### Test Your Configuration

```bash
# This should return your account info
aws sts get-caller-identity

# Expected output:
{
    "UserId": "AIDA...",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/multimodal-dev-deployer"
}
```

## ✅ **5. Install jq (JSON processor)** (Recommended)

### macOS

```bash
brew install jq
```

### Ubuntu/Debian

```bash
sudo apt install jq
```

### Test jq Installation

```bash
echo '{"name": "test"}' | jq '.name'
# Should output: "test"
```

## ✅ **6. GitHub Repository Setup** (Required)

### Make Sure Your Code is on GitHub

```bash
# If not already done:
git remote -v
# Should show your GitHub repository URL

# If no remote:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### Get Your Repository URL

```bash
# You'll need this for the setup script
git remote get-url origin
# Example: https://github.com/yourusername/background-multimodal-llm.git
```

## ✅ **7. API Keys** (Optional for Initial Setup)

You can add these later, but if you have them:

### OpenAI API Key

1. Go to [platform.openai.com](https://platform.openai.com)
2. Create account → API Keys → "Create new secret key"
3. Format: `sk-...`

### Google Gemini API Key

1. Go to [makersuite.google.com](https://makersuite.google.com)
2. Get API key
3. Format: Usually starts with letters/numbers

### Hugging Face Token

1. Go to [huggingface.co](https://huggingface.co)
2. Settings → Access Tokens → "New token"
3. Format: `hf_...`

## ✅ **8. Pre-Deployment Checklist**

Run these commands to verify everything:

```bash
# 1. Check AWS CLI
aws --version
aws sts get-caller-identity

# 2. Check you're in the right directory
pwd
ls -la | grep -E "(docker-compose.dev.yml|scripts|infrastructure)"

# 3. Check script permissions
ls -la scripts/setup-aws-dev.sh

# 4. Check your git repository
git remote get-url origin
git status
```

## 🚨 **Common Issues & Solutions**

### "AWS CLI not found"

```bash
# Check if it's in PATH
which aws
echo $PATH

# If not found, reinstall or check installation
```

### "Permission denied" for IAM operations

```bash
# Your IAM user needs CloudFormation and EC2 permissions
# Go back to IAM console and add PowerUserAccess policy
```

### "Invalid credentials"

```bash
# Reconfigure AWS CLI
aws configure
# Or check if credentials are correct
cat ~/.aws/credentials
```

### "Region not supported"

```bash
# Use a major region like us-east-1, us-west-2, eu-west-1
aws configure set region us-east-1
```

## 💰 **Cost Expectations**

### Free Tier (First 12 Months)

- **EC2 t3.micro**: 750 hours/month FREE
- **S3**: 5GB storage FREE
- **Data transfer**: 1GB/month FREE
- **Total**: $0-5/month

### After Free Tier

- **EC2 t3.micro**: ~$8/month
- **S3 + transfer**: ~$3-5/month
- **Total**: ~$10-15/month

### Cost Control

```bash
# Stop EC2 when not using (saves money)
aws ec2 stop-instances --instance-ids i-1234567890abcdef0

# Start when needed
aws ec2 start-instances --instance-ids i-1234567890abcdef0
```

## ✅ **Final Verification**

Before proceeding, make sure you can run:

```bash
# All of these should work without errors:
aws sts get-caller-identity
jq --version
git remote get-url origin
ls scripts/setup-aws-dev.sh
```

## 🚀 **Ready to Deploy?**

Once all prerequisites are complete:

```bash
# Make script executable
chmod +x scripts/setup-aws-dev.sh

# Run the setup (it will guide you through everything)
./scripts/setup-aws-dev.sh
```

The script will ask you for:

1. Your GitHub repository URL
2. AWS region (default: us-east-1)
3. API keys (optional)

Total setup time: **15-20 minutes** ⏱️
