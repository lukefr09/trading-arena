#!/bin/bash
# Start persistent MCP servers for all bots
# Each bot gets its own server on a dedicated port

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MCP_SERVER_DIR="$PROJECT_ROOT/mcp_server"

# Load environment variables if .env exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# Bot port assignments (must match BotRunner.BOT_PORTS)
declare -A BOT_PORTS=(
    ["turtle"]=8081
    ["degen"]=8082
    ["boomer"]=8083
    ["quant"]=8084
    ["doomer"]=8085
    ["gary"]=8086
    ["diana"]=8087
    ["mel"]=8088
    ["vince"]=8089
    ["rei"]=8090
    ["test"]=8091
)

# Function to start a single bot's MCP server
start_bot_server() {
    local bot_id=$1
    local port=$2

    echo "Starting MCP server for $bot_id on port $port..."

    # Check if already running
    if lsof -i :$port > /dev/null 2>&1; then
        echo "  Port $port already in use, skipping $bot_id"
        return 0
    fi

    # Start the server in background
    cd "$PROJECT_ROOT"
    BOT_ID="$bot_id" \
    CF_API_URL="${CF_API_URL}" \
    CF_API_KEY="${CF_API_KEY}" \
    FINNHUB_API_KEY="${FINNHUB_API_KEY}" \
    python3 -m mcp_server.src.server_http --port "$port" --host 127.0.0.1 \
        > "/tmp/mcp-$bot_id.log" 2>&1 &

    echo "  Started with PID $!"
}

# Parse command line args
if [ "$1" == "--bot" ] && [ -n "$2" ]; then
    # Start single bot
    bot_id="$2"
    port="${BOT_PORTS[$bot_id]}"
    if [ -z "$port" ]; then
        echo "Unknown bot: $bot_id"
        exit 1
    fi
    start_bot_server "$bot_id" "$port"
elif [ "$1" == "--all" ]; then
    # Start all bots
    for bot_id in "${!BOT_PORTS[@]}"; do
        start_bot_server "$bot_id" "${BOT_PORTS[$bot_id]}"
        sleep 0.5  # Brief delay between starts
    done
    echo "All MCP servers started. Check logs in /tmp/mcp-*.log"
elif [ "$1" == "--test" ]; then
    # Start just the test bot
    start_bot_server "test" 8091
else
    echo "Usage: $0 [--bot <bot_id>] [--all] [--test]"
    echo ""
    echo "Options:"
    echo "  --bot <bot_id>  Start MCP server for a specific bot"
    echo "  --all           Start MCP servers for all bots"
    echo "  --test          Start only the test bot MCP server"
    echo ""
    echo "Available bots: ${!BOT_PORTS[*]}"
    exit 1
fi
