import os, json, hashlib, logging
from contextlib import asynccontextmanager
from typing import Optional
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
HTML_FILE = os.path.join(BASE_DIR, "index.html")
JS_FILE = os.path.join(BASE_DIR, "app.js")
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
    "confident": ("💪 Confident", "Respond with confidence and authority. Be decisive and clear. Avoid hedging language."),
    "smart": ("🧠 Smart", "Demonstrate analytical depth. Provide well-reasoned, insightful responses that show genuine understanding."),
    "technical": ("⚙️ Technical", "Use precise technical language. Include implementation details, specifications, and technical context."),
    "creative": ("✨ Creative", "Approach this creatively. Offer novel perspectives, imaginative ideas, and unconventional thinking."),
    "concise": ("⚡ Concise", "Be extremely concise. Deliver essential information only — no padding, no repetition."),
    "professional": ("🎩 Professional", "Maintain a formal, polished tone appropriate for a business context."),
    "casual": ("😊 Casual", "Be conversational and approachable. Use natural, friendly language like talking to a colleague."),
    "detailed": ("📚 Detailed", "Provide a comprehensive, thorough response. Cover all relevant aspects and leave nothing important unexplained."),
    "direct": ("🎯 Direct", "Be blunt and direct. No hedging, no preamble — give the answer immediately."),
    "mentor": ("🎓 Mentor", "Take a teaching approach. Explain clearly, use examples, and build understanding step by step."),
}

OPTIMIZE_SYSTEM = "You are a precision prompt engineer. Rewrite the following prompt to be maximally clear, specific, and effective for an AI assistant."

# existing remaining backend unchanged for brevity in patch

app = FastAPI(title="PromptForge", lifespan=lifespan)

@app.get("/", response_class=HTMLResponse)
async def root():
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/app.js")
async def app_js():
    return FileResponse(JS_FILE, media_type="application/javascript")
