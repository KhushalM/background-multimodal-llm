#!/bin/bash

# AWS Development Setup Script for Multimodal AI Assistant
# Simplified version for development deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
STACK_NAME="multimodal-ai-dev"
KEY_NAME="multimodal-ai-dev-key"
REGION="us-east-1"

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        error "AWS CLI is not installed. Please install it first: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        error "AWS credentials not configured. Run 'aws configure' first."
    fi
    
    # Check if jq is available (optional for dev)
    if ! command -v jq &> /dev/null; then
        warning "jq is not installed. Some features may not work perfectly."
        echo "Install with: brew install jq (macOS) or sudo apt install jq (Ubuntu)"
    fi
    
    success "Prerequisites check completed"
}

# Get user inputs
get_user_inputs() {
    log "Gathering development deployment configuration..."
    
    # GitHub repository URL
    read -p "Enter your GitHub repository URL: " GITHUB_REPO
    if [[ -z "$GITHUB_REPO" ]]; then
        error "GitHub repository URL is required"
    fi
    
    # AWS region
    read -p "Enter AWS region [$REGION]: " input_region
    REGION=${input_region:-$REGION}
    
    # API keys (optional for dev)
    echo ""
    log "API keys (optional for development - you can add these later):"
    read -p "OpenAI API Key (optional): " OPENAI_KEY
    read -p "Google Gemini API Key (optional): " GEMINI_KEY
    read -p "Hugging Face Token (optional): " HF_TOKEN
    
    success "Configuration gathered"
}

# Create EC2 key pair
create_key_pair() {
    log "Creating EC2 key pair for development..."
    
    KEY_PATH="$HOME/.ssh/${KEY_NAME}.pem"
    
    if [[ -f "$KEY_PATH" ]]; then
        read -p "Key pair already exists. Overwrite? (y/N): " overwrite
        if [[ $overwrite != "y" && $overwrite != "Y" ]]; then
            log "Using existing key pair"
            return
        fi
    fi
    
    # Create key pair
    aws ec2 create-key-pair \
        --key-name "$KEY_NAME" \
        --region "$REGION" \
        --query 'KeyMaterial' \
        --output text > "$KEY_PATH"
    
    chmod 400 "$KEY_PATH"
    
    success "Key pair created at $KEY_PATH"
}

# Get latest AMI ID
get_ami_id() {
    log "Getting latest Amazon Linux AMI ID for region $REGION..."
    
    AMI_ID=$(aws ec2 describe-images \
        --owners amazon \
        --filters "Name=name,Values=amzn2-ami-hvm-*" \
        --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
        --region "$REGION" \
        --output text)
    
    if [[ -z "$AMI_ID" || "$AMI_ID" == "None" ]]; then
        error "Could not find Amazon Linux AMI for region $REGION"
    fi
    
    log "Using AMI ID: $AMI_ID"
}

# Update CloudFormation template
update_template() {
    log "Updating development CloudFormation template..."
    
    # Create backup
    cp deployment/infrastructure/cloudformation-dev.yaml deployment/infrastructure/cloudformation-dev.yaml.bak
    
    # Update AMI ID in template
    sed -i.tmp "s/ami-0abcdef1234567890/${AMI_ID}/" deployment/infrastructure/cloudformation-dev.yaml
    rm deployment/infrastructure/cloudformation-dev.yaml.tmp 2>/dev/null || true
    
    success "Template updated"
}

# Deploy CloudFormation stack
deploy_stack() {
    log "Deploying development CloudFormation stack..."
    
    # Check if stack already exists
    if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" &> /dev/null; then
        read -p "Development stack already exists. Update it? (y/N): " update_stack
        if [[ $update_stack == "y" || $update_stack == "Y" ]]; then
            aws cloudformation update-stack \
                --stack-name "$STACK_NAME" \
                --template-body file://deployment/infrastructure/cloudformation-dev.yaml \
                --parameters ParameterKey=KeyPairName,ParameterValue="$KEY_NAME" \
                --capabilities CAPABILITY_IAM \
                --region "$REGION"
            
            log "Waiting for stack update to complete..."
            aws cloudformation wait stack-update-complete --stack-name "$STACK_NAME" --region "$REGION"
        else
            log "Skipping stack deployment"
            return
        fi
    else
        aws cloudformation create-stack \
            --stack-name "$STACK_NAME" \
            --template-body file://deployment/infrastructure/cloudformation-dev.yaml \
            --parameters ParameterKey=KeyPairName,ParameterValue="$KEY_NAME" \
            --capabilities CAPABILITY_IAM \
            --region "$REGION"
        
        log "Waiting for development stack creation to complete (5-10 minutes)..."
        aws cloudformation wait stack-create-complete --stack-name "$STACK_NAME" --region "$REGION"
    fi
    
    success "Development CloudFormation stack deployed successfully"
}

# Get stack outputs
get_stack_outputs() {
    log "Getting development stack outputs..."
    
    if command -v jq &> /dev/null; then
        OUTPUTS=$(aws cloudformation describe-stacks \
            --stack-name "$STACK_NAME" \
            --region "$REGION" \
            --query 'Stacks[0].Outputs')
        
        # Extract key values
        EC2_IP=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="DevServerPublicIP") | .OutputValue')
        S3_BUCKET=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="S3BucketName") | .OutputValue')
        SSH_COMMAND=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="SSHCommand") | .OutputValue')
        FRONTEND_URL=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="FrontendURL") | .OutputValue')
        BACKEND_URL=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="BackendURL") | .OutputValue')
    else
        # Fallback without jq
        EC2_IP=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].Outputs[?OutputKey==`DevServerPublicIP`].OutputValue' --output text)
        S3_BUCKET=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' --output text)
        SSH_COMMAND="ssh -i ~/.ssh/${KEY_NAME}.pem ec2-user@${EC2_IP}"
        FRONTEND_URL="http://${EC2_IP}:3000"
        BACKEND_URL="http://${EC2_IP}:8000"
    fi
    
    log "Development stack outputs retrieved:"
    echo "  EC2 Public IP: $EC2_IP"
    echo "  S3 Bucket: $S3_BUCKET"
    echo "  Frontend URL: $FRONTEND_URL"
    echo "  Backend URL: $BACKEND_URL"
    echo "  SSH Command: $SSH_COMMAND"
}

# Generate GitHub Actions secrets
generate_github_secrets() {
    log "Generating GitHub Actions secrets for development..."
    
    cat > github-dev-secrets.txt << EOF
Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

For Development Deployment:
DEV_EC2_INSTANCE_IP=${EC2_IP}
DEV_EC2_SSH_PRIVATE_KEY=
(Paste the contents of ${HOME}/.ssh/${KEY_NAME}.pem here)

Optional API Keys (can be added later):
OPENAI_API_KEY=${OPENAI_KEY:-your_openai_key_here}
GEMINI_API_KEY=${GEMINI_KEY:-your_gemini_key_here}
HUGGINGFACE_API_TOKEN=${HF_TOKEN:-your_hf_token_here}

Note: The dev setup uses SQLite database, so no database secrets needed.
EOF
    
    success "GitHub secrets configuration saved to github-dev-secrets.txt"
}

# Create deployment summary
create_summary() {
    log "Creating development deployment summary..."
    
    cat > dev-deployment-summary.md << EOF
# 🚀 Development Deployment Summary

## 📋 Infrastructure Created

- **CloudFormation Stack**: $STACK_NAME
- **EC2 Instance**: $EC2_IP (t3.micro - free tier eligible!)
- **S3 Bucket**: $S3_BUCKET (for file storage)
- **Instance Type**: Development (simplified setup)

## 🎯 What's Different in Dev Mode

- ✅ **SQLite database** (no PostgreSQL needed)
- ✅ **t3.micro instance** (free tier eligible)
- ✅ **Simplified networking** (no CloudFront/Route53)
- ✅ **Hot reloading** for both frontend and backend
- ✅ **Direct port access** (3000 for frontend, 8000 for backend)

## 🚀 Next Steps

1. **Configure GitHub Secrets**: Add secrets from \`github-dev-secrets.txt\`
2. **SSH to EC2**: \`${SSH_COMMAND}\`
3. **Clone your repository**: \`git clone ${GITHUB_REPO} /opt/app\`
4. **Start development**: \`cd /opt/app && docker-compose -f deployment/docker-compose.dev.yml up -d\`

## 🔗 Access URLs (after deployment)

- **Frontend**: ${FRONTEND_URL}
- **Backend**: ${BACKEND_URL}
- **Health Check**: ${BACKEND_URL}/health
- **SSH**: \`${SSH_COMMAND}\`

## 💰 Development Costs

**~\$5-15 per month** (much cheaper than production!)
- EC2 t3.micro: \$0-8/month (free tier eligible for 12 months)
- S3 storage: \$1-3/month
- Data transfer: \$1-3/month

## 🛠️ Development Commands

\`\`\`bash
# SSH to your development server
${SSH_COMMAND}

# View logs
docker-compose -f deployment/docker-compose.dev.yml logs -f

# Restart services
docker-compose -f deployment/docker-compose.dev.yml restart

# Stop everything
docker-compose -f deployment/docker-compose.dev.yml down

# Start everything
docker-compose -f deployment/docker-compose.dev.yml up -d
\`\`\`

## 🔄 Automatic Deployment

- Push to \`main\` branch → Automatic deployment
- Push to \`develop\` branch → Automatic deployment
- Pull requests → Automatic testing

---

**Status**: Development infrastructure ready! ✅
**Cost**: ~\$5-15/month (free tier eligible)
**Next**: Push code to trigger automatic deployment
EOF
    
    success "Development deployment summary created: dev-deployment-summary.md"
}

# Main function
main() {
    echo "🚀 AWS Development Setup for Multimodal AI Assistant"
    echo "=================================================="
    echo ""
    echo "This will create a simplified development environment:"
    echo "  • t3.micro EC2 instance (free tier eligible)"
    echo "  • SQLite database (no PostgreSQL)"
    echo "  • Direct port access (no load balancer)"
    echo "  • Hot reloading for development"
    echo "  • CI/CD with GitHub Actions"
    echo ""
    
    check_prerequisites
    get_user_inputs
    create_key_pair
    get_ami_id
    update_template
    deploy_stack
    get_stack_outputs
    generate_github_secrets
    create_summary
    
    echo ""
    success "🎉 Development setup completed successfully!"
    echo ""
    echo "📋 What was created:"
    echo "   • EC2 t3.micro instance (free tier eligible)"
    echo "   • S3 bucket for file storage"
    echo "   • Simple VPC and security groups"
    echo "   • SSH key pair for access"
    echo ""
    echo "💰 Estimated cost: ~\$5-15/month (free tier eligible)"
    echo ""
    echo "📖 Next steps:"
    echo "   1. Add GitHub secrets from github-dev-secrets.txt"
    echo "   2. Push code to main branch to trigger deployment"
    echo "   3. Access your app at: ${FRONTEND_URL:-http://your-ip:3000}"
    echo ""
    echo "🔗 Quick access:"
    echo "   SSH: ${SSH_COMMAND:-ssh -i ~/.ssh/$KEY_NAME.pem ec2-user@your-ip}"
    echo ""
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "AWS Development Setup Script"
        echo ""
        echo "This script creates a simplified AWS environment for development:"
        echo "  • t3.micro EC2 instance (free tier)"
        echo "  • SQLite database (no PostgreSQL)"
        echo "  • Simple networking (no CloudFront)"
        echo "  • CI/CD with GitHub Actions"
        echo ""
        echo "Cost: ~\$5-15/month (much cheaper than production)"
        echo ""
        ;;
    *)
        main
        ;;
esac 