"""
FastAPI web application for Article Editor.
"""

import asyncio
import os
import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Add project root to Python path
import sys
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.processor import ArticleProcessor
from src.api.claude_client import AsyncClaudeClient
from src.utils.file_handler import FileHandler


# Pydantic models
class ProcessingRequest(BaseModel):
    filename: str
    instructions: Optional[str] = None
    chunk_size: int = 15000
    overlap: int = 500
    model: str = "claude-3-5-sonnet-20241022"
    preview_only: bool = False


class ProcessingStatus(BaseModel):
    session_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: int  # 0-100
    message: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None


class SessionInfo(BaseModel):
    session_id: str
    filename: str
    status: str
    created_at: datetime
    token_usage: Optional[Dict[str, int]] = None
    cost_estimate: Optional[float] = None
    chunks_processed: Optional[int] = None
    total_chunks: Optional[int] = None


# Global state management
class AppState:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.websocket_connections: Dict[str, WebSocket] = {}
        self.upload_dir = Path("uploads")
        self.output_dir = Path("outputs")
        self.upload_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
        # File handler
        self.file_handler = FileHandler()
        
        # Logger
        self.logger = logging.getLogger(__name__)


app_state = AppState()

# FastAPI app
app = FastAPI(
    title="Article Editor",
    description="AI-powered article editing using Claude API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory=str(project_root / "web" / "static")), name="static")
templates = Jinja2Templates(directory=str(project_root / "web" / "templates"))


# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_update(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(json.dumps(message))
            except:
                self.disconnect(session_id)


manager = ConnectionManager()


# Routes
@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the main web interface."""
    return FileResponse(str(project_root / "web" / "templates" / "index.html"))


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and validate a file for processing."""
    try:
        # Validate file type
        allowed_extensions = {'.txt', '.md', '.docx', '.doc'}
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Save uploaded file
        file_id = str(uuid.uuid4())
        file_path = app_state.upload_dir / f"{file_id}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Validate file
        validation = app_state.file_handler.validate_file(str(file_path))
        
        if not validation["valid"]:
            os.remove(file_path)
            raise HTTPException(status_code=400, detail=validation["errors"])
        
        return {
            "file_id": file_id,
            "filename": file.filename,
            "file_path": str(file_path),
            "file_info": validation["info"],
            "warnings": validation["warnings"]
        }
    
    except Exception as e:
        app_state.logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/process")
async def start_processing(
    background_tasks: BackgroundTasks,
    file_id: str = Form(...),
    filename: str = Form(...),
    instructions: Optional[str] = Form(None),
    chunk_size: int = Form(15000),
    overlap: int = Form(500),
    model: str = Form("claude-3-5-sonnet-20241022"),
    preview_only: bool = Form(False)
):
    """Start article processing."""
    try:
        # Get API key from environment
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise HTTPException(status_code=400, detail="API key not configured")
        
        # Find uploaded file
        file_path = None
        for path in app_state.upload_dir.glob(f"{file_id}_*"):
            file_path = path
            break
        
        if not file_path:
            raise HTTPException(status_code=404, detail="Uploaded file not found")
        
        # Create session
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "filename": filename,
            "file_path": str(file_path),
            "status": "pending",
            "progress": 0,
            "message": "Initializing...",
            "created_at": datetime.now(),
            "processing_request": {
                "instructions": instructions,
                "chunk_size": chunk_size,
                "overlap": overlap,
                "model": model,
                "preview_only": preview_only
            }
        }
        
        app_state.sessions[session_id] = session_data
        
        # Start background processing
        background_tasks.add_task(
            process_article_background,
            session_id,
            str(file_path),
            api_key,
            instructions,
            chunk_size,
            overlap,
            model,
            preview_only
        )
        
        return {"session_id": session_id}
    
    except Exception as e:
        app_state.logger.error(f"Processing start error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_article_background(
    session_id: str,
    file_path: str,
    api_key: str,
    instructions: Optional[str],
    chunk_size: int,
    overlap: int,
    model: str,
    preview_only: bool
):
    """Background task for article processing."""
    session = app_state.sessions[session_id]
    
    try:
        # Update status
        session["status"] = "processing"
        session["start_time"] = datetime.now()
        await manager.send_update(session_id, {
            "type": "status_update",
            "status": "processing",
            "progress": 0,
            "message": "Starting processing..."
        })
        
        # Initialize processor
        processor = ArticleProcessor(
            api_key=api_key,
            model=model,
            chunk_size=chunk_size,
            overlap=overlap
        )
        
        # Set progress callback
        async def progress_callback(current: int, total: int, message: str = ""):
            progress = int((current / total) * 100) if total > 0 else 0
            session["progress"] = progress
            session["message"] = message
            
            await manager.send_update(session_id, {
                "type": "progress_update",
                "progress": progress,
                "message": message
            })
        
        processor.set_progress_callback(lambda c, t, m: asyncio.create_task(progress_callback(c, t, m)))
        
        # Process article
        output_path = app_state.output_dir / f"{session_id}_{Path(file_path).stem}_edited.txt"
        
        result = processor.process_article(
            input_path=file_path,
            output_path=str(output_path) if not preview_only else None,
            instructions=instructions,
            preview_only=preview_only,
            create_backup=False
        )
        
        if result["success"]:
            session["status"] = "completed"
            session["end_time"] = datetime.now()
            session["result"] = result
            session["output_path"] = str(output_path) if not preview_only else None
            
            await manager.send_update(session_id, {
                "type": "completion",
                "status": "completed",
                "progress": 100,
                "result": {
                    "token_usage": result["token_usage"],
                    "cost_estimate": result["cost_estimate"],
                    "chunks_count": result["chunks_count"],
                    "edited_text": result["edited_text"] if preview_only else None
                }
            })
        else:
            session["status"] = "failed"
            session["error"] = result["error"]
            session["end_time"] = datetime.now()
            
            await manager.send_update(session_id, {
                "type": "error",
                "status": "failed",
                "error": result["error"]
            })
    
    except Exception as e:
        app_state.logger.error(f"Background processing error: {e}")
        session["status"] = "failed"
        session["error"] = str(e)
        session["end_time"] = datetime.now()
        
        await manager.send_update(session_id, {
            "type": "error",
            "status": "failed",
            "error": str(e)
        })


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket, session_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(session_id)


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session information."""
    if session_id not in app_state.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = app_state.sessions[session_id]
    return {
        "session_id": session_id,
        "status": session["status"],
        "progress": session.get("progress", 0),
        "message": session.get("message", ""),
        "created_at": session["created_at"],
        "start_time": session.get("start_time"),
        "end_time": session.get("end_time"),
        "error": session.get("error"),
        "result": session.get("result")
    }


@app.get("/api/sessions")
async def list_sessions():
    """List all sessions."""
    sessions = []
    for session_id, session in app_state.sessions.items():
        sessions.append({
            "session_id": session_id,
            "filename": session["filename"],
            "status": session["status"],
            "created_at": session["created_at"],
            "token_usage": session.get("result", {}).get("token_usage"),
            "cost_estimate": session.get("result", {}).get("cost_estimate")
        })
    
    return {"sessions": sorted(sessions, key=lambda x: x["created_at"], reverse=True)}


@app.get("/api/download/{session_id}")
async def download_result(session_id: str):
    """Download processed file."""
    if session_id not in app_state.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = app_state.sessions[session_id]
    
    if session["status"] != "completed":
        raise HTTPException(status_code=400, detail="Session not completed")
    
    output_path = session.get("output_path")
    if not output_path or not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Output file not found")
    
    return FileResponse(
        output_path,
        filename=f"{session['filename']}_edited.txt",
        media_type="text/plain"
    )


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and its files."""
    if session_id not in app_state.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = app_state.sessions[session_id]
    
    # Clean up files
    try:
        if "file_path" in session and os.path.exists(session["file_path"]):
            os.remove(session["file_path"])
        
        if "output_path" in session and os.path.exists(session["output_path"]):
            os.remove(session["output_path"])
    except:
        pass
    
    # Remove session
    del app_state.sessions[session_id]
    
    return {"message": "Session deleted"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "active_sessions": len(app_state.sessions),
        "websocket_connections": len(manager.active_connections)
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logging.basicConfig(level=logging.INFO)
    app_state.logger.info("Article Editor web application started")


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )