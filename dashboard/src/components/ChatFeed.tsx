/**
 * ChatFeed component - shows bot messages and trash talk
 */

import type { Message } from '../types';

interface ChatFeedProps {
  messages: Message[];
}

export function ChatFeed({ messages }: ChatFeedProps) {
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="panel chat-panel">
      <div className="panel-header">
        <span className="panel-title">Bot Chat</span>
        <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
          {messages.length} messages
        </span>
      </div>
      <div className="panel-content">
        <div className="chat-feed">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`chat-message ${msg.is_dm ? 'dm' : 'public'}`}
            >
              <div className="chat-header">
                <span className="chat-from">{msg.from_name}</span>
                {msg.is_dm && (
                  <span className="chat-dm-badge">
                    DM to {msg.to_bot}
                  </span>
                )}
                <span className="chat-time">{formatTime(msg.created_at)}</span>
              </div>
              <div className="chat-content">{msg.content}</div>
            </div>
          ))}

          {messages.length === 0 && (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 'var(--spacing-lg)' }}>
              No messages yet
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
