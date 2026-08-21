import os
import json
import asyncio
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
import shutil
from app.schemas import ChatRequest, ChatResponse
from app.graph.workflow import agent_app
from app.websocket_manager import ws_manager
from app.config import settings

# Import services
from app.services.pdf_processor import pdf_processor
from app.services.vector_store import vector_store_service

app = FastAPI(
    title="Dynamic Agentic System API",
    version="1.0.0",
    description="Multi-Agent Pipeline with RAG, Text-to-SQL, Math Execution, and Live Tracing"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve PDF Screenshot Assets for Citations
screenshots_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "screenshots"))
if not os.path.exists(screenshots_dir):
    os.makedirs(screenshots_dir, exist_ok=True)

app.mount("/screenshots", StaticFiles(directory=screenshots_dir), name="screenshots")

# Upload Directory setup
UPLOAD_DIR = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "uploads")))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------------------------
# 1. Healthcheck Endpoint
# -------------------------------------------------------------------
@app.get("/health")
def health_check():
    return {
        "status": "online",
        "configured_top_k": settings.DEFAULT_TOP_K,
        "configured_temperature": settings.DEFAULT_TEMPERATURE
    }

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Welcome to the Dynamic Agentic System API",
        "docs": "/docs",
        "health": "/health"
    }


# -------------------------------------------------------------------
# 2. WebSocket Live Tracing Endpoint
# -------------------------------------------------------------------
@app.websocket("/ws/trace/{client_id}")
async def websocket_trace_endpoint(websocket: WebSocket, client_id: str):
    await ws_manager.connect(client_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(client_id)


# -------------------------------------------------------------------
# 3. REST Chat Execution Endpoint
# -------------------------------------------------------------------
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        initial_state = {
            "user_query": request.user_query,
            "persona": request.persona,
            "client_id": request.client_id
        }

        if request.client_id:
            # Non-blocking: fire-and-forget so we don't stall before graph starts
            ws_manager.fire_trace_event(request.client_id, "workflow_start", "running")

        output_state = await asyncio.to_thread(agent_app.invoke, initial_state)

        if request.client_id:
            # Awaited: must flush before we return the HTTP response
            await ws_manager.send_trace_event(request.client_id, "workflow_complete", "success", {
                "route_target": output_state.get("route_target"),
                "persona": output_state.get("persona")
            })

        return ChatResponse(
            final_answer=output_state.get("final_answer", ""),
            persona=output_state.get("persona", "Auto"),
            route_target=output_state.get("route_target", "doc"),
            source_metadata=output_state.get("source_metadata", {}),
            suggested_queries=output_state.get("suggested_queries", [])
        )

    except Exception as e:
        err_msg = str(e)
        if "rate-limit" in err_msg.lower() or "429" in err_msg or "rate limit" in err_msg.lower() or "upstream" in err_msg.lower():
            print(f"[CHAT ENDPOINT WARNING] Upstream rate limit encountered: {e}")
            user_msg = "The AI service is temporarily rate-limited upstream. Please retry shortly or verify configured fallback models."
        else:
            print(f"[CHAT ENDPOINT ERROR] Workflow failed: {e}")
            user_msg = err_msg

        if request.client_id:
            await ws_manager.send_trace_event(request.client_id, "workflow_error", "error", {"error": user_msg})
        raise HTTPException(status_code=500, detail=user_msg)


@app.post("/api/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    async def event_generator():
        try:
            # Serialise Pydantic ChatMessage objects → plain dicts for state/prompts
            history_dicts = [{"role": m.role, "content": m.content} for m in request.chat_history]

            initial_state = {
                "user_query": request.user_query,
                "persona": request.persona,
                "client_id": request.client_id,
                "chat_history": history_dicts,
            }

            # 1. Emit workflow start — non-blocking fire-and-forget
            if request.client_id:
                ws_manager.fire_trace_event(
                    request.client_id,
                    "workflow_start",
                    "running",
                    {"user_query": request.user_query, "persona": request.persona},
                )

            # 2. Walk astream_events(version="v2") —
            #    This is the only LangGraph API that emits on_chat_model_stream
            #    events for every individual LLM token, enabling word-by-word
            #    rendering.  on_chain_end events carry each node's output dict
            #    so we can build the final done payload without a separate invoke.
            output_state: dict = {}

            async for event in agent_app.astream_events(initial_state, version="v2"):
                kind = event.get("event", "")

                # -----------------------------------------------------------
                # TOKEN STREAM — yield formatter tokens immediately as SSE.
                #
                # IMPORTANT: astream_events fires on_chat_model_stream for
                # EVERY LLM call in the graph — including the classifier and
                # the suggestion LLM.  The classifier uses with_structured_output()
                # so its chunk.content is the raw JSON schema string, e.g.:
                #   '{"persona": "General Assistant", "route_target": "general"}'
                # Forwarding those tokens causes the raw JSON to render on screen.
                #
                # Fix: filter by the LangGraph node name stored in
                # event["metadata"]["langgraph_node"] and only forward chunks
                # originating from answer_formatter_node.
                # -----------------------------------------------------------
                if kind == "on_chat_model_stream":
                    # Only forward tokens produced by the answer formatter
                    node_tag = event.get("metadata", {}).get("langgraph_node", "")
                    if node_tag != "answer_formatter_node":
                        continue

                    chunk = event.get("data", {}).get("chunk")
                    if chunk is not None:
                        token_text = ""
                        if isinstance(chunk.content, str):
                            token_text = chunk.content
                        elif isinstance(chunk.content, list):
                            # Some providers (Anthropic, Google) return content blocks
                            token_text = "".join(
                                part.get("text", "") if isinstance(part, dict) else str(part)
                                for part in chunk.content
                            )
                        if token_text:
                            # Emit stream_start before the very first token so the
                            # frontend knows to clear "Thinking..." and show the cursor
                            if not output_state.get("_stream_started"):
                                output_state["_stream_started"] = True
                                yield f"data: {json.dumps({'type': 'stream_start'})}\n\n"
                            # Yield token immediately — no local buffering
                            yield f"data: {json.dumps({'type': 'token', 'token': token_text})}\n\n"

                # -----------------------------------------------------------
                # NODE COMPLETION — accumulate state + send trace telemetry
                # -----------------------------------------------------------
                elif kind == "on_chain_end":
                    node_output = event.get("data", {}).get("output")
                    node_name = event.get("name", "")

                    # Merge every node's output dict into output_state so we
                    # can build the done payload after the graph finishes
                    if isinstance(node_output, dict):
                        output_state.update(node_output)

                    # Forward per-node telemetry to the WebSocket trace panel
                    if request.client_id and node_name:
                        ws_manager.fire_trace_event(
                            request.client_id,
                            event_type=f"node_{node_name}",
                            status="executing",
                            payload={
                                "node": node_name,
                                "route_target": output_state.get("route_target"),
                                "persona": output_state.get("persona"),
                            },
                        )

            # 3. Build the done payload from the fully-accumulated state.
            #    This is sent ONCE, after all graph nodes have completed.
            done_payload = {
                "type": "done",
                "final_answer": output_state.get("final_answer", "Sorry, I couldn't generate a response."),
                "suggested_queries": output_state.get("suggested_queries", []),
                "source_metadata": output_state.get("source_metadata", {}),
                "route_target": output_state.get("route_target", "general"),
                "persona": output_state.get("persona", request.persona),
            }

            # 4. Flush workflow_complete to the trace panel before the SSE done line
            if request.client_id:
                await ws_manager.send_trace_event(
                    request.client_id,
                    "workflow_complete",
                    "success",
                    {
                        "route_target": output_state.get("route_target"),
                        "persona": output_state.get("persona"),
                    },
                )

            yield f"data: {json.dumps(done_payload)}\n\n"

        except Exception as e:
            err_msg = str(e)
            if "rate-limit" in err_msg.lower() or "429" in err_msg or "rate limit" in err_msg.lower() or "upstream" in err_msg.lower():
                print(f"[STREAM ENDPOINT WARNING] Upstream rate limit encountered: {e}")
                user_msg = "Notice: The upstream AI provider is temporarily rate-limited. Please retry shortly."
            else:
                print(f"[STREAM ENDPOINT ERROR] Streaming error: {e}")
                user_msg = err_msg

            if request.client_id:
                await ws_manager.send_trace_event(
                    request.client_id, "workflow_error", "error", {"error": user_msg}
                )
            yield f"data: {json.dumps({'type': 'error', 'message': user_msg})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            # Prevent Nginx / any reverse proxy from buffering SSE chunks.
            # Without this, chunks are held until the buffer fills (typically 4–8 kB),
            # which defeats per-token streaming entirely.
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
        },
    )

# -------------------------------------------------------------------
# 5. Document Management & Upload Endpoints
# -------------------------------------------------------------------
@app.get("/api/doc-status")
async def check_doc_status():
    has_docs = vector_store_service.has_existing_documents()
    return {"has_existing_documents": has_docs}


@app.post("/api/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    replace_existing: bool = Form(default=False)
):
    try:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported.")

        file_path = UPLOAD_DIR / file.filename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if replace_existing:
            vector_store_service.clear_vectors()

        chunks = pdf_processor.process_pdf(str(file_path))
        vector_store_service.add_document_chunks(chunks)

        return {
            "status": "success",
            "filename": file.filename,
            "message": f"Successfully indexed '{file.filename}'",
            "replace_existing": replace_existing,
            "total_chunks": len(chunks)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))