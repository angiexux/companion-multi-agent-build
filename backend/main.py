import asyncio
import json
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from agents.orchestrator import run_pipeline
from character.manager import list_characters, load_bio, character_dir
from character.companion import CompanionSession

# ── In-memory job store ────────────────────────────────────────────────────

_jobs: dict[str, dict] = {}          # job_id → {status, manifest, error}
_job_waiters: dict[str, asyncio.Queue] = {}   # job_id → event queue for WS


# ── App ────────────────────────────────────────────────────────────────────

app = FastAPI(title="Companion Multi-Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/response models ────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str
    second_prompt: str | None = None


class GenerateResponse(BaseModel):
    job_id: str


class ActivateRequest(BaseModel):
    character_id: str


class ActivateResponse(BaseModel):
    session_id: str


# ── Active companion sessions ──────────────────────────────────────────────

_sessions: dict[str, CompanionSession] = {}


# ── REST endpoints ─────────────────────────────────────────────────────────

@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "running", "manifest": None, "error": None}
    _job_waiters[job_id] = asyncio.Queue()
    asyncio.create_task(_run_job(job_id, req.prompt, req.second_prompt))
    return GenerateResponse(job_id=job_id)


@app.post("/activate", response_model=ActivateResponse)
async def activate(req: ActivateRequest):
    try:
        session = CompanionSession(req.character_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    session_id = str(uuid.uuid4())
    _sessions[session_id] = session
    return ActivateResponse(session_id=session_id)


@app.get("/characters")
async def get_characters():
    return [m.model_dump() for m in list_characters()]


@app.get("/characters/{character_id}")
async def get_character(character_id: str):
    try:
        bio = load_bio(character_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Character not found")
    return bio.model_dump()


@app.get("/characters/{character_id}/portrait")
async def get_portrait(character_id: str):
    path = character_dir(character_id) / "portrait.png"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Portrait not found")
    return FileResponse(path, media_type="image/png")


@app.get("/characters/{character_id}/voice")
async def get_voice(character_id: str):
    path = character_dir(character_id) / "voice_sample.mp3"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Voice sample not found")
    return FileResponse(path, media_type="audio/mpeg")


# ── WebSocket: generation progress ────────────────────────────────────────

@app.websocket("/ws/generate/{job_id}")
async def ws_generate(websocket: WebSocket, job_id: str):
    await websocket.accept()

    if job_id not in _job_waiters:
        await websocket.send_json({"event": "error", "message": "Unknown job"})
        await websocket.close()
        return

    queue = _job_waiters[job_id]

    try:
        while True:
            event = await asyncio.wait_for(queue.get(), timeout=120)
            await websocket.send_json(event)
            if event.get("event") in ("generation_complete", "error"):
                break
    except asyncio.TimeoutError:
        await websocket.send_json({"event": "error", "message": "Generation timed out"})
    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()


# ── WebSocket: companion chat ──────────────────────────────────────────────

@app.websocket("/ws/companion/{session_id}")
async def ws_companion(websocket: WebSocket, session_id: str):
    await websocket.accept()

    session = _sessions.get(session_id)
    if not session:
        await websocket.send_json({"type": "error", "message": "Session not found"})
        await websocket.close()
        return

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            if msg.get("type") != "user_message":
                continue

            async for kind, data in session.respond(msg["text"]):
                await websocket.send_json({"type": kind, "data": data})
    except WebSocketDisconnect:
        pass
    finally:
        _sessions.pop(session_id, None)


# ── Background job runner ──────────────────────────────────────────────────

async def _run_job(job_id: str, prompt: str, second_prompt: str | None):
    queue = _job_waiters[job_id]

    async def emit(event: dict):
        await queue.put(event)

    try:
        manifest = await run_pipeline(prompt, emit, second_prompt)
        _jobs[job_id]["status"] = "complete"
        _jobs[job_id]["manifest"] = manifest
    except Exception as e:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(e)
        await emit({"event": "error", "agent": "orchestrator", "message": str(e)})
