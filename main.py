import os, json, hmac, hashlib, secrets
from contextlib import asynccontextmanager
from typing import Optional
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
HTML_FILE = os.path.join(BASE_DIR, "index.html")

BEACON_URL = "https://beaconapp.freddiesparrow.co.uk/update.json"
APP_VERSION = "1.0.0"
APP_ID = "promptforge"

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


# ── helpers ──────────────────────────────────────────────────────────────────

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {
        "keys": {},
        "local_model": "gemma3:4b",
        "ollama_url": "http://localhost:11434",
        "dev_mode": False,
    }

def save_config(cfg: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


# ── models ───────────────────────────────────────────────────────────────────

class OptimizeRequest(BaseModel):
    prompt: str

class SendRequest(BaseModel):
    prompt: str
    provider: str
    model: str
    tone: Optional[str] = None

class SettingsUpdate(BaseModel):
    keys: dict = {}
    local_model: Optional[str] = "gemma3:4b"
    ollama_url: Optional[str] = "http://localhost:11434"

class DevActivate(BaseModel):
    code: str

class PullRequest(BaseModel):
    model: str


# ── app ──────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.path.exists(CONFIG_FILE):
        save_config(load_config())
    yield

app = FastAPI(title="PromptForge", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def root():
    with open(HTML_FILE) as f:
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
    }


@app.post("/api/settings")
async def update_settings(req: SettingsUpdate):
    cfg = load_config()
    for k, v in req.keys.items():
        if v and not v.startswith("•"):
            cfg.setdefault("keys", {})[k] = v
        elif not v:
            cfg.get("keys", {}).pop(k, None)
    cfg["local_model"] = req.local_model
    cfg["ollama_url"] = req.ollama_url
    save_config(cfg)
    return {"status": "saved"}


@app.post("/api/dev/activate")
async def activate_dev(req: DevActivate):
    """Verify developer code (hash comparison only — no plaintext stored or returned)."""
    if _sha256(req.code) == _DEV_CODE_HASH:
        cfg = load_config()
        cfg["dev_mode"] = True
        save_config(cfg)
        return {"status": "verified", "dev_mode": True}
    raise HTTPException(status_code=403, detail="Invalid code")


@app.post("/api/dev/deactivate")
async def deactivate_dev():
    cfg = load_config()
    cfg["dev_mode"] = False
    save_config(cfg)
    return {"status": "deactivated"}


@app.get("/api/updates/check")
async def check_updates():
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(BEACON_URL)
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
        return {"current": APP_VERSION, "latest": APP_VERSION, "update_available": False}


@app.post("/api/ollama/pull")
async def pull_model(req: PullRequest):
    """Pull a model via Ollama API, streaming progress back as newline-delimited JSON."""
    from fastapi.responses import StreamingResponse
    import asyncio

    cfg = load_config()
    base = cfg.get("ollama_url", "http://localhost:11434")
    model_name = req.model.strip()
    if not model_name:
        raise HTTPException(status_code=400, detail="Model name required")

    async def stream_pull():
        try:
            async with httpx.AsyncClient(timeout=600) as client:
                async with client.stream("POST", f"{base}/api/pull",
                                         json={"name": model_name, "stream": True}) as r:
                    async for line in r.aiter_lines():
                        if line:
                            yield line + "\n"
        except Exception as e:
            import json as _json
            yield _json.dumps({"status": "error", "error": str(e)}) + "\n"

    return StreamingResponse(stream_pull(), media_type="application/x-ndjson")


@app.get("/api/ollama/status")
async def ollama_status():
    cfg = load_config()
    base = cfg.get("ollama_url", "http://localhost:11434")
    model = cfg.get("local_model", "gemma3:4b")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{base}/api/tags")
            tags = r.json().get("models", [])
            names = [t.get("name", "") for t in tags]
            has_model = any(model.split(":")[0] in m for m in names)
            return {"running": True, "model_available": has_model, "model": model, "available_models": names}
    except Exception as e:
        return {"running": False, "model_available": False, "error": str(e)}


@app.post("/api/optimize")
async def optimize_prompt(req: OptimizeRequest):
    cfg = load_config()
    base = cfg.get("ollama_url", "http://localhost:11434")
    model = cfg.get("local_model", "gemma3:4b")
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(f"{base}/api/generate", json={
                "model": model,
                "prompt": OPTIMIZE_SYSTEM + req.prompt,
                "stream": False,
                "options": {"temperature": 0.25, "num_predict": 512},
            })
            data = r.json()
            return {"optimized": data.get("response", "").strip(), "model": model}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama unavailable: {e}")


@app.post("/api/send")
async def send_to_ai(req: SendRequest):
    cfg = load_config()
    provider = PROVIDERS.get(req.provider)
    if not provider:
        raise HTTPException(status_code=400, detail="Unknown provider")

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
                if "error" in data:
                    raise HTTPException(status_code=400, detail=data["error"].get("message", "API error"))
                return {
                    "response": data["choices"][0]["message"]["content"],
                    "usage": data.get("usage", {}),
                    "provider": req.provider,
                    "model": req.model,
                }

            elif provider["type"] == "anthropic":
                r = await client.post(
                    f"{provider['base_url']}/messages",
                    headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                    json={"model": req.model, "max_tokens": 4096, "messages": [{"role": "user", "content": final_prompt}]},
                )
                data = r.json()
                if "error" in data:
                    raise HTTPException(status_code=400, detail=data["error"].get("message", "API error"))
                usage = data.get("usage", {})
                return {
                    "response": data["content"][0]["text"],
                    "usage": {"input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens")},
                    "provider": req.provider,
                    "model": req.model,
                }

            elif provider["type"] == "google":
                r = await client.post(
                    f"{provider['base_url']}/models/{req.model}:generateContent?key={api_key}",
                    json={"contents": [{"parts": [{"text": final_prompt}]}]},
                )
                data = r.json()
                if "error" in data:
                    raise HTTPException(status_code=400, detail=data["error"].get("message", "API error"))
                meta = data.get("usageMetadata", {})
                return {
                    "response": data["candidates"][0]["content"]["parts"][0]["text"],
                    "usage": {"input_tokens": meta.get("promptTokenCount"), "output_tokens": meta.get("candidatesTokenCount")},
                    "provider": req.provider,
                    "model": req.model,
                }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    print("\n  PromptForge  →  http://localhost:7474\n")
    uvicorn.run("main:app", host="127.0.0.1", port=7474, reload=False)
