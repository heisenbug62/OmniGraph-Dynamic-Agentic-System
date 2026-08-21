"""
websocket_manager.py — WebSocket Connection Manager
====================================================
Manages live trace connections to the frontend TracePanel.

Key optimization: `fire_trace_event()` wraps the async send in
`asyncio.create_task()` so the caller never awaits it — WebSocket I/O
is dispatched in the background without blocking graph execution.
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Maps client_id → active WebSocket instance
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info("WebSocket client connected: %s", client_id)

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info("WebSocket client disconnected: %s", client_id)

    async def send_trace_event(
        self,
        client_id: str,
        event_type: str = "trace_event",
        status: str = "info",
        payload: Optional[Dict[str, Any]] = None,
        *args,
        **kwargs,
    ):
        """
        Sends a trace event to a specific client over WebSocket.
        Handles both positional arguments and keyword argument aliases.

        This method is still an `async def` so it can be awaited directly
        when strict ordering matters (e.g., the workflow_complete event).
        For fire-and-forget telemetry use `fire_trace_event()`.
        """
        if client_id not in self.active_connections:
            return

        websocket = self.active_connections[client_id]

        # Accept 'event' as a keyword alias for event_type (legacy callers)
        event_name = kwargs.get("event", event_type)

        message: Dict[str, Any] = {
            "event": event_name,
            "status": status,
            "payload": payload or kwargs.get("data") or {},
        }

        # Elevate frequently accessed fields to the top level for the TracePanel
        if isinstance(payload, dict):
            if "node" in payload:
                message["node"] = payload["node"]
            if "route_target" in payload:
                message["route_target"] = payload["route_target"]
            if "persona" in payload:
                message["persona"] = payload["persona"]

        try:
            await websocket.send_text(json.dumps(message))
        except Exception as exc:
            logger.error("Error sending WebSocket message to %s: %s", client_id, exc)
            self.disconnect(client_id)

    def fire_trace_event(
        self,
        client_id: str,
        event_type: str = "trace_event",
        status: str = "info",
        payload: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> None:
        """
        NON-BLOCKING telemetry dispatch.

        Schedules `send_trace_event` as a background asyncio Task so the
        caller does NOT await it.  Graph execution continues immediately
        while the WebSocket message is flushed concurrently.

        Usage (no `await` needed):
            ws_manager.fire_trace_event(client_id, "node_classifier", "executing", {...})
        """
        if client_id not in self.active_connections:
            return  # Skip scheduling if the client isn't connected

        asyncio.create_task(
            self.send_trace_event(client_id, event_type, status, payload, **kwargs)
        )


ws_manager = ConnectionManager()