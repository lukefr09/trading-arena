/**
 * ArenaRoom - Durable Object for WebSocket connections with hibernation
 */

import type { WebSocketMessage } from './types';

interface WebSocketConnection {
  webSocket: WebSocket;
  id: string;
}

export class ArenaRoom implements DurableObject {
  private state: DurableObjectState;
  private connections: Map<string, WebSocket> = new Map();

  constructor(state: DurableObjectState) {
    this.state = state;
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    // Internal broadcast endpoint
    if (url.pathname === '/broadcast' && request.method === 'POST') {
      const message = await request.json() as WebSocketMessage;
      this.broadcast(JSON.stringify(message));
      return new Response('OK', { status: 200 });
    }

    // WebSocket upgrade
    if (request.headers.get('Upgrade') === 'websocket') {
      return this.handleWebSocket(request);
    }

    // Connection count
    if (url.pathname === '/connections') {
      return new Response(JSON.stringify({
        count: this.connections.size,
      }), {
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response('Not found', { status: 404 });
  }

  private async handleWebSocket(request: Request): Promise<Response> {
    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);

    // Generate unique connection ID
    const connectionId = crypto.randomUUID();

    // Accept the WebSocket with hibernation support
    this.state.acceptWebSocket(server, [connectionId]);

    // Store connection
    this.connections.set(connectionId, server);

    // Send welcome message
    server.send(JSON.stringify({
      type: 'connected',
      data: { connectionId },
    }));

    return new Response(null, {
      status: 101,
      webSocket: client,
    });
  }

  async webSocketMessage(ws: WebSocket, message: string | ArrayBuffer): Promise<void> {
    // Handle incoming messages from clients
    try {
      const data = JSON.parse(message as string);

      // Ping/pong for keepalive
      if (data.type === 'ping') {
        ws.send(JSON.stringify({ type: 'pong' }));
        return;
      }

      // Could handle other client messages here
    } catch {
      // Ignore parse errors
    }
  }

  async webSocketClose(ws: WebSocket, code: number, reason: string, wasClean: boolean): Promise<void> {
    // Find and remove the connection
    for (const [id, socket] of this.connections.entries()) {
      if (socket === ws) {
        this.connections.delete(id);
        break;
      }
    }
  }

  async webSocketError(ws: WebSocket, error: unknown): Promise<void> {
    // Find and remove the errored connection
    for (const [id, socket] of this.connections.entries()) {
      if (socket === ws) {
        this.connections.delete(id);
        break;
      }
    }
  }

  private broadcast(message: string): void {
    // Get all hibernated WebSockets
    const sockets = this.state.getWebSockets();

    for (const socket of sockets) {
      try {
        socket.send(message);
      } catch {
        // Socket closed, will be cleaned up
      }
    }
  }
}
