#!/bin/bash
# Run a trading round - starts MCP servers if needed, then runs orchestrator

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
VENV_PYTHON="$PROJECT_ROOT/venv/bin/python3"

# Create logs directory
mkdir -p "$LOG_DIR"

# Log file with timestamp
LOG_FILE="$LOG_DIR/round-$(date +%Y%m%d-%H%M%S).log"

{
    echo "=== Trading Round Start: $(date) ==="

    # Load environment
    if [ -f "$PROJECT_ROOT/.env" ]; then
        export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
    fi

    # Ensure MCP servers are running
    echo "Checking MCP servers..."
    RUNNING_SERVERS=$(lsof -i :8081-8090 2>/dev/null | grep LISTEN | wc -l || echo "0")
    if [ "$RUNNING_SERVERS" -lt 5 ]; then
        echo "Starting MCP servers..."
        "$SCRIPT_DIR/start_mcp_servers.sh" --all
        sleep 5  # Give servers time to start
    else
        echo "MCP servers already running ($RUNNING_SERVERS ports)"
    fi

    # Run the orchestrator
    echo "Running orchestrator..."
    cd "$PROJECT_ROOT"
    "$VENV_PYTHON" -m orchestrator.src.main

    echo "=== Trading Round Complete: $(date) ==="

} 2>&1 | tee "$LOG_FILE"

# Clean up old logs (keep last 50)
cd "$LOG_DIR" && ls -t round-*.log | tail -n +51 | xargs -r rm --
