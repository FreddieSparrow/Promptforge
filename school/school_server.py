import json
import os
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
POLICY_FILE = BASE_DIR / "academic_integrity_policy.txt"
CONTROLS_FILE = BASE_DIR / "admin_controls.json"
STUDENT_HTML = BASE_DIR / "static" / "student.html"
ADMIN_HTML = BASE_DIR / "static" / "admin.html"
SCHOOL_JS = BASE_DIR / "static" / "school.js"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("SCHOOL_AI_MODEL", "gemma3:4b")
MAX_PROMPT_LENGTH = 8000

app = FastAPI(title="PromptForge Schools", version="0.1.0")


class AskRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_LENGTH)
    mode: str = "learning_support"
    room: str = "default"
    student_year: Optional[str] = None


class AdminSettings(BaseModel):
    mode: str
    exam_mode_enabled: bool
    banned_coursework_enabled: bool
    default_model: str


def load_policy() -> str:
    return POLICY_FILE.read_text(encoding="utf-8")


def load_controls() -> dict:
    return json.loads(CONTROLS_FILE.read_text(encoding="utf-8"))


def save_controls(data: dict) -> None:
    CONTROLS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def build_school_prompt(req: AskRequest) -> str:
    controls = load_controls()
    policy = load_policy()
    room_rules = controls.get("per_room_access_rules", {}).get("rooms", {}).get(req.room) or controls.get("per_room_access_rules", {}).get("rooms", {}).get("default", {})

    allowed_modes = room_rules.get("allowed_modes", [])
    if allowed_modes and req.mode not in allowed_modes:
        raise HTTPException(status_code=403, detail=f"Mode '{req.mode}' is not allowed in room '{req.room}'.")

    extra_rules = []
    if controls.get("banned_coursework_mode", {}).get("enabled", True):
        extra_rules.append("Do not produce full assessed coursework, final submissions, NEA work, portfolios, or plagiarism-ready answers.")
    if controls.get("exam_mode_policy", {}).get("enabled", False) or req.mode == "exam_mode":
        extra_rules.append("Exam mode is active: provide general conceptual help only. Do not answer live exam/test questions directly.")

    return f"""{policy}

School mode: {req.mode}
Room: {req.room}
Student year/group: {req.student_year or 'not specified'}

Additional active controls:
{chr(10).join('- ' + rule for rule in extra_rules) if extra_rules else '- Standard learning support mode'}

Student request:
{req.prompt}

Respond as a helpful school learning assistant. Prefer hints, explanations, and guided questions over final answers.
"""


def pick_model(room: str) -> str:
    controls = load_controls()
    room_rules = controls.get("per_room_access_rules", {}).get("rooms", {}).get(room) or controls.get("per_room_access_rules", {}).get("rooms", {}).get("default", {})
    allowed = room_rules.get("allowed_models", [])
    if DEFAULT_MODEL in allowed:
        return DEFAULT_MODEL
    return allowed[0] if allowed else DEFAULT_MODEL


@app.get("/", response_class=HTMLResponse)
async def home():
    return STUDENT_HTML.read_text(encoding="utf-8")


@app.get("/admin", response_class=HTMLResponse)
async def admin():
    return ADMIN_HTML.read_text(encoding="utf-8")


@app.get("/school.js")
async def school_js():
    return FileResponse(SCHOOL_JS, media_type="application/javascript")


@app.get("/api/status")
async def status():
    controls = load_controls()
    try:
        async with httpx.AsyncClient(timeout=4) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            r.raise_for_status()
            models = [m.get("name", "") for m in r.json().get("models", [])]
        ollama = {"running": True, "models": models}
    except Exception as e:
        ollama = {"running": False, "error": str(e), "models": []}
    return {"service": "PromptForge Schools", "controls": controls, "ollama": ollama}


@app.post("/api/ask")
async def ask(req: AskRequest, request: Request):
    model = pick_model(req.room)
    full_prompt = build_school_prompt(req)
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 900},
                },
            )
            r.raise_for_status()
            data = r.json()
            answer = data.get("response", "").strip()
            if not answer:
                raise HTTPException(status_code=502, detail="The local model returned an empty response.")
            return {"answer": answer, "model": model, "mode": req.mode, "room": req.room}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Local AI unavailable: {e}")


@app.get("/api/admin/settings")
async def get_admin_settings():
    controls = load_controls()
    return controls


@app.post("/api/admin/settings")
async def update_admin_settings(settings: AdminSettings):
    controls = load_controls()
    controls["mode"] = settings.mode
    controls.setdefault("exam_mode_policy", {})["enabled"] = settings.exam_mode_enabled
    controls.setdefault("banned_coursework_mode", {})["enabled"] = settings.banned_coursework_enabled

    approved = controls.setdefault("approved_models", {})
    models = approved.setdefault("models", [])
    if settings.default_model not in models:
        models.insert(0, settings.default_model)

    save_controls(controls)
    return {"status": "saved", "controls": controls}


if __name__ == "__main__":
    import uvicorn
    print("\nPromptForge Schools → http://0.0.0.0:7474\n")
    uvicorn.run("school_server:app", host="0.0.0.0", port=7474, reload=False)
