#!/bin/bash
# Run a trading round - starts MCP servers if needed, then runs orchestrator

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
VENV_PYTHON="$PROJECT_ROOT/venv/bin/python3"
LOCK_FILE="$PROJECT_ROOT/.round-running.lock"

# Create logs directory
mkdir -p "$LOG_DIR"

# Check for lock - skip if another round is running
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Another round is already running (PID $PID). Skipping."
        exit 0
    else
        echo "Stale lock file found. Removing."
        rm -f "$LOCK_FILE"
    fi
fi

# Create lock
echo $$ > "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

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

    # Run the orchestrator with 30 min timeout
    echo "Running orchestrator (30 min timeout)..."
    cd "$PROJECT_ROOT"
    timeout 1800 "$VENV_PYTHON" -m orchestrator.src.main || {
        echo "WARNING: Round timed out or failed!"
        # Kill any stuck claude processes for bots
        pkill -f "mcp-config-" 2>/dev/null || true
    }

    echo "=== Trading Round Complete: $(date) ==="

} 2>&1 | tee "$LOG_FILE"

# Clean up old logs (keep last 50)
cd "$LOG_DIR" && ls -t round-*.log | tail -n +51 | xargs -r rm --
