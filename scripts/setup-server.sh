#!/bin/bash
# Setup script for Trading Arena on DigitalOcean (Ubuntu 22.04+)
# Run as root or with sudo

set -e

echo "=== Trading Arena Server Setup ==="

# Update system
echo "Updating system packages..."
apt update && apt upgrade -y

# Install Node.js 20 (for Claude Code CLI)
echo "Installing Node.js 20..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# Install Python 3.11+ and pip
echo "Installing Python..."
apt install -y python3 python3-pip python3-venv

# Install uv (for Alpaca MCP server)
echo "Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Install Claude Code CLI
echo "Installing Claude Code CLI..."
npm install -g @anthropic-ai/claude-code

# Create app directory
echo "Setting up app directory..."
mkdir -p /opt/trading-arena
cd /opt/trading-arena

# Clone the repo (replace with your repo URL)
# git clone https://github.com/YOUR_USERNAME/trading-arena.git .

echo ""
echo "=== Manual steps remaining ==="
echo ""
echo "1. Clone your repo:"
echo "   cd /opt/trading-arena"
echo "   git clone https://github.com/YOUR_USERNAME/trading-arena.git ."
echo ""
echo "2. Install Python dependencies:"
echo "   pip3 install -r mcp-server/requirements.txt"
echo "   pip3 install -r orchestrator/requirements.txt"
echo ""
echo "3. Create .env file with your API keys:"
echo "   cp .env.example .env"
echo "   nano .env"
echo ""
echo "4. Set up Alpaca credentials in D1 database:"
echo "   - Create 10 Alpaca paper trading accounts at https://alpaca.markets"
echo "   - Add API keys to the bots table via Cloudflare dashboard or wrangler"
echo ""
echo "5. Authenticate Claude Code:"
echo "   claude auth"
echo ""
echo "6. Test a bot run:"
echo "   cd /opt/trading-arena/orchestrator"
echo "   python3 -m src.main --test"
echo ""
echo "Setup complete! Server is ready for Trading Arena."
