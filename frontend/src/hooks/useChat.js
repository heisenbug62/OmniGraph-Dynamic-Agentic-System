import { useState, useCallback } from 'react';

// ---------------------------------------------------------------------------
// History window: the maximum number of past messages sent to the backend.
// Must match (or be ≤) HISTORY_WINDOW in backend/app/schemas.py.
// We send at most 10 entries = 5 full user/assistant exchange pairs.
// ---------------------------------------------------------------------------
const HISTORY_WINDOW = 10;

/**
 * Strips every frontend-only field from a displayed message so the payload
 * sent to the backend is lean: only `role` and `content` survive.
 * We also exclude any currently-streaming placeholder ("Thinking...") message.
 */
function buildHistoryPayload(messages) {
  return messages
    .filter(
      (m) =>
        (m.role === 'user' || m.role === 'assistant') &&
        !m.isStreaming &&                    // skip in-flight placeholder
        m.content &&
        m.content !== 'Thinking...'
    )
    .map(({ role, content }) => ({ role, content }))  // keep only role + content
    .slice(-HISTORY_WINDOW);                // trim to window before sending
}

export function useChat(clientId) {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentPersona, setCurrentPersona] = useState('Auto');

  const sendMessage = useCallback(async (text) => {
    if (!text || !text.trim() || isLoading) return;

    const userMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: text,
    };

    const botMessageId = `bot_${Date.now()}`;
    const initialBotMessage = {
      id: botMessageId,
      role: 'assistant',
      content: 'Thinking...',
      isStreaming: false,
      persona: currentPersona,
      metadata: {},
      suggested_queries: [],
    };

    // Capture the history BEFORE appending the new messages — the current
    // user turn isn't committed yet, so the backend receives only past turns.
    // The backend then appends user_query itself when answering.
    setMessages((prev) => {
      return [...prev, userMessage, initialBotMessage];
    });

    // Build history from the current state snapshot (before this turn)
    // We use a functional approach: capture the pre-append messages inline.
    setIsLoading(true);

    try {
      // Take a snapshot of messages BEFORE the new turn was pushed.
      // Because React batches, we need to grab the previous state via a ref
      // pattern or closure. We read `messages` from the outer closure — this
      // is safe because sendMessage is memoised and `messages` is stable at
      // the point of this call.
      const chatHistory = buildHistoryPayload(messages);

      const response = await fetch('http://localhost:8000/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_query: text,
          persona: currentPersona,
          client_id: clientId,
          chat_history: chatHistory,   // ← new: prior turns for multi-turn memory
        }),
      });

      if (!response.ok) throw new Error(`Server status: ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data:')) continue;

          try {
            const data = JSON.parse(trimmed.replace(/^data:\s*/, ''));

            if (data.type === 'stream_start') {
              // First real token is about to arrive — clear the placeholder
              // and raise the isStreaming flag so the pulsing cursor renders.
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === botMessageId
                    ? { ...msg, content: '', isStreaming: true }
                    : msg
                )
              );

            } else if (data.type === 'token') {
              // Append each token immediately via functional setState so React
              // triggers a re-render per chunk — word-by-word typewriter effect.
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === botMessageId
                    ? { ...msg, content: msg.content + data.token, isStreaming: true }
                    : msg
                )
              );

            } else if (data.type === 'done') {
              // Graph finished — replace streamed content with the authoritative
              // final_answer, attach metadata/suggestions, drop streaming cursor.
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === botMessageId
                    ? {
                        ...msg,
                        content: data.final_answer,
                        isStreaming: false,
                        persona: data.persona || msg.persona,
                        suggested_queries: data.suggested_queries || [],
                        metadata: {
                          ...msg.metadata,
                          route_target: data.route_target,
                          source_metadata: data.source_metadata,
                        },
                      }
                    : msg
                )
              );

            } else if (data.type === 'error') {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === botMessageId
                    ? { ...msg, content: `**Error:** ${data.message}`, isStreaming: false }
                    : msg
                )
              );
            }
          } catch (err) {
            console.error('Failed to parse SSE line:', err);
          }
        }
      }
    } catch (error) {
      console.error('Chat stream error:', error);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === botMessageId ? { ...msg, content: '⚠️ Connection error. Please try again.' } : msg
        )
      );
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, currentPersona, clientId, messages]);

  return {
    messages,
    isLoading,
    currentPersona,
    setCurrentPersona,
    sendMessage,
  };
}