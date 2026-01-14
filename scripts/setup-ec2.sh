#!/bin/bash
# EC2 Ubuntu Setup Script for Agentic RAG

set -e

echo "=================================="
echo "Agentic RAG - EC2 Setup Script"
echo "=================================="

# Update system
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
echo "Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "Docker installed successfully"
else
    echo "Docker already installed"
fi

# Install Docker Compose
echo "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "Docker Compose installed successfully"
else
    echo "Docker Compose already installed"
fi

# Create application directory
APP_DIR="/opt/agentic-rag"
echo "Setting up application directory at $APP_DIR..."
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# Copy files if running from repo directory
if [ -f "docker-compose.yml" ]; then
    echo "Copying application files..."
    cp -r . $APP_DIR/
fi

# Create .env file if it doesn't exist
if [ ! -f "$APP_DIR/.env" ]; then
    echo "Creating .env file..."
    cat > $APP_DIR/.env << EOF
# OpenAI API Key (required)
OPENAI_API_KEY=your-api-key-here

# Optional: Change port
# PORT=8000
EOF
    echo "Please edit $APP_DIR/.env and add your OpenAI API key"
fi

# Create data directories
mkdir -p $APP_DIR/data/uploads
mkdir -p $APP_DIR/data/vectordb

# Set permissions
chmod 755 $APP_DIR/data

echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Edit the .env file with your OpenAI API key:"
echo "   nano $APP_DIR/.env"
echo ""
echo "2. Start the application:"
echo "   cd $APP_DIR"
echo "   docker-compose up -d"
echo ""
echo "3. Access the application at:"
echo "   http://$(curl -s ifconfig.me):8000"
echo ""
echo "4. For production with Nginx:"
echo "   docker-compose --profile production up -d"
echo ""
