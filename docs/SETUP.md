# Complete Setup Guide

This guide provides detailed instructions for setting up and running the Agentic RAG system.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (5 minutes)](#quick-start)
3. [Local Development Setup](#local-development-setup)
4. [Docker Setup](#docker-setup)
5. [EC2 Production Setup](#ec2-production-setup)
6. [Configuration](#configuration)
7. [Verification](#verification)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required
- **Python 3.10+** (for local development)
- **OpenAI API Key** with access to:
  - GPT-4o (Vision & Generation)
  - text-embedding-3-small (Embeddings)
  - o1-mini (Reasoning/Verification)

### Optional
- **Docker & Docker Compose** (for containerized deployment)
- **Git** (for cloning repository)

### Hardware Recommendations
| Deployment | RAM | Storage | CPU |
|------------|-----|---------|-----|
| Development | 4GB | 10GB | 2 cores |
| Production | 8GB+ | 50GB+ | 4+ cores |

---

## Quick Start

```bash
# 1. Clone repository
git clone https://github.com/akhanna222/agentic-rag.git
cd agentic-rag

# 2. Create environment file
cp .env.example .env

# 3. Add your OpenAI API key
echo "OPENAI_API_KEY=sk-your-key-here" >> .env

# 4. Run with Docker
docker-compose up -d

# 5. Access the application
open http://localhost:8001
```

---

## Local Development Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/akhanna222/agentic-rag.git
cd agentic-rag
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
# On Linux/macOS:
source venv/bin/activate

# On Windows:
.\venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### Step 4: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your settings
nano .env  # or use any text editor
```

**Required settings in `.env`:**
```bash
OPENAI_API_KEY=sk-your-openai-api-key-here
```

**Optional settings:**
```bash
# API Authentication (recommended for production)
REQUIRE_API_KEY=true
RAG_API_KEY=your-secure-random-key

# Model customization
VISION_MODEL=gpt-4o
REASONING_MODEL=o1-mini

# Server settings
HOST=0.0.0.0
PORT=8000
```

### Step 5: Create Data Directories

```bash
mkdir -p data/uploads data/vectordb
```

### Step 6: Run the Application

```bash
# Option 1: Using the run script
chmod +x scripts/run-local.sh
./scripts/run-local.sh

# Option 2: Direct command
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Step 7: Access the Application

- **Web UI**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health

---

## Docker Setup

### Step 1: Install Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Logout and login again for group changes
```

### Step 2: Install Docker Compose

```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Step 3: Configure Environment

```bash
cp .env.example .env
nano .env  # Add your OPENAI_API_KEY
```

### Step 4: Build and Run

```bash
# Build and start in background
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Step 5: Production with Nginx (HTTPS)

```bash
# Create SSL directory and add certificates
mkdir -p ssl
# Add your cert.pem and key.pem to ssl/

# Run with Nginx
docker-compose --profile production up -d
```

---

## EC2 Production Setup

### Step 1: Launch EC2 Instance

**Recommended specs:**
- **AMI**: Ubuntu 22.04 LTS
- **Instance Type**: t3.medium or larger
- **Storage**: 30GB+ EBS
- **Security Group**:
  - SSH (22) from your IP
  - HTTP (80) from anywhere
  - HTTPS (443) from anywhere
  - Custom TCP (8000) from anywhere (or VPC only)

### Step 2: Connect to Instance

```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

### Step 3: Run Setup Script

```bash
# Clone repository
git clone https://github.com/akhanna222/agentic-rag.git
cd agentic-rag

# Make script executable and run
chmod +x scripts/setup-ec2.sh
./scripts/setup-ec2.sh
```

### Step 4: Configure Application

```bash
cd /opt/agentic-rag

# Edit environment file
nano .env
```

Add your configuration:
```bash
OPENAI_API_KEY=sk-your-key-here
REQUIRE_API_KEY=true
RAG_API_KEY=generate-a-secure-key-here
```

### Step 5: Start the Service

```bash
docker-compose up -d
```

### Step 6: Configure Domain (Optional)

1. Point your domain to EC2 public IP
2. Add SSL certificates:
```bash
# Using Let's Encrypt
sudo apt install certbot
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/key.pem
```

3. Enable Nginx with SSL:
```bash
docker-compose --profile production up -d
```

### Step 7: Set Up Auto-Start (Optional)

```bash
# Create systemd service
sudo nano /etc/systemd/system/agentic-rag.service
```

Add:
```ini
[Unit]
Description=Agentic RAG Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/agentic-rag
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable agentic-rag
sudo systemctl start agentic-rag
```

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `REQUIRE_API_KEY` | No | false | Enable API authentication |
| `RAG_API_KEY` | No | - | API key for auth |
| `VISION_MODEL` | No | gpt-4o | Model for document parsing |
| `EMBEDDING_MODEL` | No | text-embedding-3-small | Embedding model |
| `REASONING_MODEL` | No | o1-mini | Verification model |
| `GENERATION_MODEL` | No | gpt-4o | Answer generation model |
| `CHUNK_SIZE` | No | 1000 | Characters per chunk |
| `CHUNK_OVERLAP` | No | 200 | Overlap between chunks |
| `TOP_K_RETRIEVAL` | No | 5 | Chunks to retrieve |
| `MAX_VERIFICATION_ATTEMPTS` | No | 5 | Max retry attempts |
| `CONFIDENCE_THRESHOLD` | No | 0.8 | Min confidence score |
| `HOST` | No | 0.0.0.0 | Server host |
| `PORT` | No | 8000 | Server port |

### Generate Secure API Key

```bash
# Using Python
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Using OpenSSL
openssl rand -base64 32
```

---

## Verification

### Check Health

```bash
curl http://localhost:8001/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "api_key_required": false
}
```

### Test API

```bash
# Create a disease
curl -X POST "http://localhost:8001/api/v1/diseases?name=test-disease"

# List diseases
curl http://localhost:8001/api/v1/diseases

# Upload a document (example with a text file)
echo "Diabetes symptoms include increased thirst and frequent urination." > test.txt
curl -X POST -F "file=@test.txt" http://localhost:8001/upload/test-disease

# Query
curl "http://localhost:8001/api/v1/ask?disease=test-disease&question=What%20are%20symptoms?&verify=false"
```

---

## Troubleshooting

### Common Issues

#### 1. "OPENAI_API_KEY not set"
```bash
# Check if .env file exists and is loaded
cat .env | grep OPENAI

# Make sure it's exported (for local dev)
export $(grep -v '^#' .env | xargs)
```

#### 2. "Port 8000 already in use"
```bash
# Find and kill the process
lsof -i :8000
kill -9 <PID>

# Or use a different port
PORT=8001 python -m uvicorn main:app --port 8001
```

#### 3. Docker permission denied
```bash
sudo usermod -aG docker $USER
# Logout and login again
```

#### 4. ChromaDB errors
```bash
# Clear the vector database
rm -rf data/vectordb/*

# Restart the application
docker-compose restart
```

#### 5. Memory issues on EC2
```bash
# Add swap space
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### View Logs

```bash
# Docker logs
docker-compose logs -f agentic-rag

# Local development
# Logs appear in terminal

# Check specific container
docker logs agentic-rag -f --tail 100
```

### Reset Everything

```bash
# Stop containers
docker-compose down

# Remove data
rm -rf data/uploads/* data/vectordb/*

# Rebuild
docker-compose up -d --build
```

---

## Next Steps

1. **Upload Documents**: Use the web UI to create a disease and upload medical documents
2. **Test Queries**: Ask questions about your uploaded documents
3. **Integrate with n8n**: See [n8n Integration Guide](../README.md#n8n-integration)
4. **Review Roadmap**: See [ROADMAP.md](./ROADMAP.md) for planned features
