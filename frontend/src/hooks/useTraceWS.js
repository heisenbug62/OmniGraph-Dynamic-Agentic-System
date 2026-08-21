import { useState, useEffect, useRef } from 'react';

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://127.0.0.1:8000';

// Only these are real pipeline steps worth showing — everything else
// (RunnableLambda, RunnableSequence, RunnableWithFallbacks, etc.) is
// LangChain's internal execution wrapping, not something a user should see.
// Keep this in sync with the node names registered in workflow.py.
const MEANINGFUL_NODES = new Set([
  'classifier_node',
  'route_decision',
  'doc_rag_node',
  'db_sql_node',
  'math_exec_node',
  'suggestion_node',
  'answer_formatter_node',
]);

function isMeaningfulEvent(data) {
  // Always keep top-level workflow markers — they have no `node` field.
  if (data.event === 'workflow_start' || data.event === 'workflow_complete') {
    return true;
  }
  return MEANINGFUL_NODES.has(data.node);
}

export function useTraceWS(clientId) {
  const [events, setEvents] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    if (!clientId) return;

    const wsUrl = `${WS_BASE_URL}/ws/trace/${clientId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log(`[WS Connected]: ${clientId}`);
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (isMeaningfulEvent(data)) {
          setEvents((prev) => [...prev, data]);
        }
      } catch {
        console.warn('Received non-JSON trace event:', event.data);
      }
    };

    ws.onclose = () => {
      console.log(`[WS Disconnected]: ${clientId}`);
      setIsConnected(false);
    };

    ws.onerror = (err) => {
      console.error('[WS Error]:', err);
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [clientId]);

  const clearEvents = () => setEvents([]);

  return { events, isConnected, clearEvents };
}