import os, json, hashlib, logging
from contextlib import asynccontextmanager
from typing import Optional
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
HTML_FILE = os.path.join(BASE_DIR, "index.html")
LOG_FILE = os.path.join(BASE_DIR, "promptforge.log")

BEACON_URL = "https://beaconapp.freddiesparrow.co.uk/update.json"
APP_VERSION = "1.0.1"
APP_ID = "promptforge"
MAX_PROMPT_LENGTH = 12000
MAX_MODEL_NAME_LENGTH = 120

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger("promptforge")

# Developer account verification — stored as SHA-256 hash only. No plaintext in source.
_DEV_CODE_HASH = "6eaabe383f13d0c4ef926de8ed1984614970f952f03b9de2b5a9ba2b6c3b3c1f"

PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "type": "openai_compat",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1", "o1-mini"],
    },
    "anthropic": {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "type": "anthropic",
        "models": ["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
    },
    "google": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "type": "google",
        "models": ["gemini-2.5-pro", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
    },
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "type": "openai_compat",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "gemma2-9b-it", "mixtral-8x7b-32768"],
    },
    "mistral": {
        "name": "Mistral",
        "base_url": "https://api.mistral.ai/v1",
        "type": "openai_compat",
        "models": ["mistral-large-latest", "mistral-small-latest", "codestral-latest"],
    },
    "xai": {
        "name": "xAI Grok",
        "base_url": "https://api.x.ai/v1",
        "type": "openai_compat",
        "models": ["grok-2-latest", "grok-2-mini"],
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "type": "openai_compat",
        "models": [
            "openai/gpt-4o",
            "anthropic/claude-3.5-sonnet",
            "meta-llama/llama-3.3-70b-instruct",
            "google/gemini-2.0-flash-001",
        ],
    },
}

TONES = {
    "confident":    ("💪 Confident",    "Respond with confidence and authority. Be decisive and clear. Avoid hedging language."),
    "smart":        ("🧠 Smart",        "Demonstrate analytical depth. Provide well-reasoned, insightful responses that show genuine understanding."),
    "technical":    ("⚙️ Technical",    "Use precise technical language. Include implementation details, specifications, and technical context."),
    "creative":     ("✨ Creative",     "Approach this creatively. Offer novel perspectives, imaginative ideas, and unconventional thinking."),
    "concise":      ("⚡ Concise",      "Be extremely concise. Deliver essential information only — no padding, no repetition."),
    "professional": ("🎩 Professional", "Maintain a formal, polished tone appropriate for a business context."),
    "casual":       ("😊 Casual",       "Be conversational and approachable. Use natural, friendly language like talking to a colleague."),
    "detailed":     ("📚 Detailed",     "Provide a comprehensive, thorough response. Cover all relevant aspects and leave nothing important unexplained."),
    "direct":       ("🎯 Direct",       "Be blunt and direct. No hedging, no preamble — give the answer immediately."),
    "mentor":       ("🎓 Mentor",       "Take a teaching approach. Explain clearly, use examples, and build understanding step by step."),
}

OPTIMIZE_SYSTEM = (
    "You are a precision prompt engineer. Rewrite the following prompt to be maximally clear, "
    "specific, and effective for an AI assistant.\n\n"
    "Rules:\n"
    "- Remove filler words, redundancy, and vagueness\n"
    "- Make the intent explicit and unambiguous\n"
    "- Improve structure and logical flow\n"
    "- Preserve every key detail and constraint from the original\n"
    "- Do NOT add requirements the user didn't ask for\n"
    "- Return ONLY the rewritten prompt — no explanation, no preamble\n\n"
    "Optimise this prompt:\n"
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _default_config() -> dict:
    return {
        "keys": {},
        "local_model": "gemma3:4b",
        "ollama_url": "http://localhost:11434",
        "dev_mode": False,
    }


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            default = _default_config()
            default.update(cfg)
            default["keys"] = cfg.get("keys", {}) if isinstance(cfg.get("keys", {}), dict) else {}
            return default
        except Exception:
            logger.exception("Failed to read config.json; using defaults")
    return _default_config()


def save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def validate_prompt(prompt: str):
    if not prompt or not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required")
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise HTTPException(status_code=413, detail=f"Prompt too large. Maximum is {MAX_PROMPT_LENGTH} characters.")


def clean_ollama_url(url: Optional[str]) -> str:
    raw = (url or "http://localhost:11434").strip().rstrip("/")
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=400, detail="Invalid Ollama URL. Use something like http://localhost:11434")
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise HTTPException(status_code=400, detail="For safety, Ollama URL must be localhost only")
    return raw


def model_matches(configured: str, available: str) -> bool:
    configured = configured.strip()
    available = available.strip()
    return available == configured or available.split(":", 1)[0] == configured.split(":", 1)[0]


class OptimizeRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_LENGTH)


class SendRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_LENGTH)
    provider: str
    model: str = Field(..., min_length=1, max_length=MAX_MODEL_NAME_LENGTH)
    tone: Optional[str] = None


class SettingsUpdate(BaseModel):
    keys: dict = {}
    local_model: Optional[str] = Field(default="gemma3:4b", max_length=MAX_MODEL_NAME_LENGTH)
    ollama_url: Optional[str] = "http://localhost:11434"


class DevActivate(BaseModel):
    code: str = Field(..., min_length=1, max_length=200)


class PullRequest(BaseModel):
    model: str = Field(..., min_length=1, max_length=MAX_MODEL_NAME_LENGTH)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.path.exists(CONFIG_FILE):
        save_config(load_config())
    logger.info("PromptForge started")
    yield
    logger.info("PromptForge stopped")


app = FastAPI(title="PromptForge", lifespan=lifespan)


@app.middleware("http")
async def localhost_only(request: Request, call_next):
    host = request.client.host if request.client else "unknown"
    if host not in {"127.0.0.1", "::1", "localhost"}:
        logger.warning("Blocked non-local request from %s", host)
        raise HTTPException(status_code=403, detail="PromptForge only accepts local connections")
    return await call_next(request)


@app.get("/", response_class=HTMLResponse)
async def root():
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/providers")
async def get_providers():
    return {pid: {"name": p["name"], "models": p["models"]} for pid, p in PROVIDERS.items()}


@app.get("/api/tones")
async def get_tones():
    return {k: {"label": v[0], "instruction": v[1]} for k, v in TONES.items()}


@app.get("/api/settings")
async def get_settings():
    cfg = load_config()
    masked = {k: ("•" * 8 + v[-4:]) if v else "" for k, v in cfg.get("keys", {}).items()}
    return {
        "keys_masked": masked,
        "providers_configured": [k for k, v in cfg.get("keys", {}).items() if v],
        "local_model": cfg.get("local_model", "gemma3:4b"),
        "ollama_url": cfg.get("ollama_url", "http://localhost:11434"),
        "dev_mode": cfg.get("dev_mode", False),
        "config_security": "local_plaintext_config",
    }


@app.post("/api/settings")
async def update_settings(req: SettingsUpdate):
    cfg = load_config()
    for k, v in req.keys.items():
        if k not in PROVIDERS:
            continue
        if isinstance(v, str) and v and not v.startswith("•"):
            cfg.setdefault("keys", {})[k] = v.strip()
        elif not v:
            cfg.get("keys", {}).pop(k, None)
    cfg["local_model"] = (req.local_model or "gemma3:4b").strip()
    cfg["ollama_url"] = clean_ollama_url(req.ollama_url)
    save_config(cfg)
    logger.info("Settings updated. Providers configured: %s", list(cfg.get("keys", {}).keys()))
    return {"status": "saved"}


@app.post("/api/dev/activate")
async def activate_dev(req: DevActivate):
    if _sha256(req.code) == _DEV_CODE_HASH:
        cfg = load_config()
        cfg["dev_mode"] = True
        save_config(cfg)
        logger.info("Developer mode activated")
        return {"status": "verified", "dev_mode": True}
    logger.warning("Invalid developer code attempted")
    raise HTTPException(status_code=403, detail="Invalid code")


@app.post("/api/dev/deactivate")
async def deactivate_dev():
    cfg = load_config()
    cfg["dev_mode"] = False
    save_config(cfg)
    logger.info("Developer mode deactivated")
    return {"status": "deactivated"}


@app.get("/api/updates/check")
async def check_updates():
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(BEACON_URL)
            r.raise_for_status()
            data = r.json()
            pf = data.get("apps", {}).get(APP_ID, {})
            latest = pf.get("latest", APP_VERSION)
            return {
                "current": APP_VERSION,
                "latest": latest,
                "update_available": latest != APP_VERSION,
                "changelog": pf.get("changelog", ""),
                "download": pf.get("download", ""),
            }
    except Exception:
        logger.exception("Update check failed")
        return {"current": APP_VERSION, "latest": APP_VERSION, "update_available": False}


@app.post("/api/ollama/pull")
async def pull_model(req: PullRequest):
    from fastapi.responses import StreamingResponse

    cfg = load_config()
    base = clean_ollama_url(cfg.get("ollama_url", "http://localhost:11434"))
    model_name = req.model.strip()
    if not model_name:
        raise HTTPException(status_code=400, detail="Model name required")

    async def stream_pull():
        try:
            async with httpx.AsyncClient(timeout=600) as client:
                async with client.stream("POST", f"{base}/api/pull", json={"name": model_name, "stream": True}) as r:
                    async for line in r.aiter_lines():
                        if line:
                            yield line + "\n"
        except Exception as e:
            logger.exception("Ollama pull failed for %s", model_name)
            yield json.dumps({"status": "error", "error": str(e)}) + "\n"

    return StreamingResponse(stream_pull(), media_type="application/x-ndjson")


@app.get("/api/ollama/status")
async def ollama_status():
    cfg = load_config()
    base = clean_ollama_url(cfg.get("ollama_url", "http://localhost:11434"))
    model = cfg.get("local_model", "gemma3:4b")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{base}/api/tags")
            r.raise_for_status()
            tags = r.json().get("models", [])
            names = [t.get("name", "") for t in tags]
            has_model = any(model_matches(model, m) for m in names)
            return {"running": True, "model_available": has_model, "model": model, "available_models": names}
    except Exception as e:
        logger.exception("Ollama status check failed")
        return {"running": False, "model_available": False, "model": model, "available_models": [], "error": str(e)}


@app.post("/api/optimize")
async def optimize_prompt(req: OptimizeRequest):
    validate_prompt(req.prompt)
    cfg = load_config()
    base = clean_ollama_url(cfg.get("ollama_url", "http://localhost:11434"))
    model = cfg.get("local_model", "gemma3:4b")
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(f"{base}/api/generate", json={
                "model": model,
                "prompt": OPTIMIZE_SYSTEM + req.prompt,
                "stream": False,
                "options": {"temperature": 0.25, "num_predict": 512},
            })
            r.raise_for_status()
            data = r.json()
            optimized = data.get("response", "").strip()
            if not optimized:
                raise HTTPException(status_code=502, detail="Ollama returned an empty response")
            return {"optimized": optimized, "model": model}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Prompt optimisation failed")
        raise HTTPException(status_code=503, detail=f"Ollama unavailable: {e}")


@app.post("/api/send")
async def send_to_ai(req: SendRequest):
    validate_prompt(req.prompt)
    cfg = load_config()
    provider = PROVIDERS.get(req.provider)
    if not provider:
        raise HTTPException(status_code=400, detail="Unknown provider")
    if req.model not in provider["models"]:
        raise HTTPException(status_code=400, detail="Model is not listed for this provider")

    api_key = cfg.get("keys", {}).get(req.provider)
    if not api_key:
        raise HTTPException(status_code=401, detail=f"No API key for {req.provider}. Add it in Settings.")

    final_prompt = req.prompt
    if req.tone and req.tone in TONES:
        final_prompt = f"{req.prompt}\n\n---\n{TONES[req.tone][1]}"

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            if provider["type"] == "openai_compat":
                r = await client.post(
                    f"{provider['base_url']}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": req.model, "messages": [{"role": "user", "content": final_prompt}]},
                )
                data = r.json()
                if r.status_code >= 400 or "error" in data:
                    detail = data.get("error", {}).get("message", f"API error {r.status_code}")
                    raise HTTPException(status_code=400, detail=detail)
                return {
                    "response": data["choices"][0]["message"]["content"],
                    "usage": data.get("usage", {}),
                    "provider": req.provider,
                    "model": req.model,
                }

            if provider["type"] == "anthropic":
                r = await client.post(
                    f"{provider['base_url']}/messages",
                    headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                    json={"model": req.model, "max_tokens": 4096, "messages": [{"role": "user", "content": final_prompt}]},
                )
                data = r.json()
                if r.status_code >= 400 or "error" in data:
                    detail = data.get("error", {}).get("message", f"API error {r.status_code}")
                    raise HTTPException(status_code=400, detail=detail)
                usage = data.get("usage", {})
                return {
                    "response": data["content"][0]["text"],
                    "usage": {"input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens")},
                    "provider": req.provider,
                    "model": req.model,
                }

            if provider["type"] == "google":
                r = await client.post(
                    f"{provider['base_url']}/models/{req.model}:generateContent",
                    params={"key": api_key},
                    json={"contents": [{"parts": [{"text": final_prompt}]}]},
                )
                data = r.json()
                if r.status_code >= 400 or "error" in data:
                    detail = data.get("error", {}).get("message", f"API error {r.status_code}")
                    raise HTTPException(status_code=400, detail=detail)
                meta = data.get("usageMetadata", {})
                return {
                    "response": data["candidates"][0]["content"]["parts"][0]["text"],
                    "usage": {"input_tokens": meta.get("promptTokenCount"), "output_tokens": meta.get("candidatesTokenCount")},
                    "provider": req.provider,
                    "model": req.model,
                }

        raise HTTPException(status_code=400, detail="Unsupported provider type")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Provider request failed for %s/%s", req.provider, req.model)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    print("\n  PromptForge  →  http://localhost:7474\n")
    uvicorn.run("main:app", host="127.0.0.1", port=7474, reload=False)
