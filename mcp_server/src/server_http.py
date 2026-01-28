"""HTTP/SSE MCP Server for Trading Arena.

Run as a persistent service instead of spawning per-request.
Usage: BOT_ID=test python -m mcp_server.src.server_http --port 8081
"""

import argparse
import os
from contextlib import asynccontextmanager

import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse

from mcp.server.sse import SseServerTransport

# Import everything from the main server
from .server import server, BOT_ID

# Create SSE transport
sse = SseServerTransport("/messages/")


async def handle_sse(request):
    """Handle SSE connection for MCP."""
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await server.run(
            streams[0], streams[1], server.create_initialization_options()
        )


async def handle_messages(request):
    """Handle incoming MCP messages."""
    await sse.handle_post_message(request.scope, request.receive, request._send)


async def health(request):
    """Health check endpoint."""
    return JSONResponse({
        "status": "ok",
        "bot_id": BOT_ID,
        "server": "trading-arena-mcp"
    })


# Create Starlette app
app = Starlette(
    debug=True,
    routes=[
        Route("/health", health),
        Route("/sse", handle_sse),
        Route("/messages/", handle_messages, methods=["POST"]),
    ],
)


def main():
    parser = argparse.ArgumentParser(description="Trading Arena MCP HTTP Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    args = parser.parse_args()

    print(f"Starting Trading Arena MCP Server for bot '{BOT_ID}' on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
