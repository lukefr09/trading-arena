#!/bin/bash
# VPS Setup Script for Trading Arena Orchestrator
# Run on a fresh DigitalOcean Ubuntu 22.04 droplet

set -e

echo "=== Trading Arena VPS Setup ==="

# Update system
echo "Updating system packages..."
apt-get update
apt-get upgrade -y

# Install dependencies
echo "Installing dependencies..."
apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    curl \
    unzip \
    jq

# Create trading user
echo "Creating trading user..."
useradd -m -s /bin/bash trading || true
mkdir -p /home/trading

# Install Node.js (for Claude Code)
echo "Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Install Claude Code CLI
echo "Installing Claude Code CLI..."
npm install -g @anthropic-ai/claude-code

# Clone repository
echo "Cloning repository..."
cd /home/trading
if [ -d "trading-arena" ]; then
    cd trading-arena
    git pull
else
    git clone https://github.com/YOUR_USERNAME/trading-arena.git
    cd trading-arena
fi

# Set up Python virtual environment
echo "Setting up Python environment..."
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r orchestrator/requirements.txt
pip install -r mcp-server/requirements.txt

# Create environment file template
echo "Creating .env template..."
cat > /home/trading/trading-arena/.env.template << 'EOF'
# Cloudflare API
CF_API_URL=https://trading-arena-api.YOUR_SUBDOMAIN.workers.dev
CF_API_KEY=your-api-key-here

# Finnhub
FINNHUB_API_KEY=your-finnhub-key-here

# Claude (optional - uses default)
CLAUDE_MODEL=claude-opus-4-20250514
EOF

if [ ! -f /home/trading/trading-arena/.env ]; then
    cp /home/trading/trading-arena/.env.template /home/trading/trading-arena/.env
    echo "Created .env file - please edit with your credentials"
fi

# Create MCP config for Claude Code
echo "Creating MCP config..."
mkdir -p /home/trading/.claude
cat > /home/trading/trading-arena/orchestrator/mcp-config.json << 'EOF'
{
  "mcpServers": {
    "finnhub": {
      "command": "/home/trading/trading-arena/venv/bin/python",
      "args": ["-m", "mcp-server.src.server"],
      "cwd": "/home/trading/trading-arena"
    }
  }
}
EOF

# Create run script
echo "Creating run script..."
cat > /home/trading/trading-arena/orchestrator/run.sh << 'EOF'
#!/bin/bash
cd /home/trading/trading-arena
source venv/bin/activate
source .env

# Check if market is open (rough check)
HOUR=$(TZ=America/New_York date +%H)
DAY=$(date +%u)

# Skip weekends
if [ "$DAY" -gt 5 ]; then
    echo "Weekend - skipping"
    exit 0
fi

# Skip outside market hours (9-16 ET)
if [ "$HOUR" -lt 9 ] || [ "$HOUR" -gt 16 ]; then
    echo "Outside market hours - skipping"
    exit 0
fi

# Run orchestrator
python -m orchestrator.src.main 2>&1 | tee -a /home/trading/trading-arena/logs/orchestrator.log
EOF
chmod +x /home/trading/trading-arena/orchestrator/run.sh

# Create logs directory
mkdir -p /home/trading/trading-arena/logs

# Set ownership
chown -R trading:trading /home/trading

# Set up cron job
echo "Setting up cron job..."
cat > /etc/cron.d/trading-arena << 'EOF'
# Trading Arena - Run during market hours (ET)
# First run at 9:30 AM ET, then every hour until 4 PM ET
30 9 * * 1-5 trading cd /home/trading/trading-arena/orchestrator && ./run.sh >> /home/trading/trading-arena/logs/cron.log 2>&1
0 10-16 * * 1-5 trading cd /home/trading/trading-arena/orchestrator && ./run.sh >> /home/trading/trading-arena/logs/cron.log 2>&1
EOF

# Restart cron
systemctl restart cron

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Edit /home/trading/trading-arena/.env with your credentials"
echo "2. Authenticate Claude Code: su - trading && claude --login"
echo "3. Initialize the game: python scripts/init-game.py"
echo "4. Set game status to running: python scripts/set-game-status.py running"
echo ""
echo "Monitor logs: tail -f /home/trading/trading-arena/logs/orchestrator.log"
