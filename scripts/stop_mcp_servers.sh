#!/bin/bash
# Stop all running MCP servers

echo "Stopping all MCP servers..."

# Kill by port range (8081-8091)
for port in {8081..8091}; do
    pid=$(lsof -ti :$port 2>/dev/null)
    if [ -n "$pid" ]; then
        echo "Stopping server on port $port (PID $pid)"
        kill $pid 2>/dev/null || true
    fi
done

# Also kill any remaining server_http processes
pkill -f "mcp_server.src.server_http" 2>/dev/null || true

echo "Done."
