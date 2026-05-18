# PromptForge

Local-first AI prompt optimisation toolkit.

PromptForge rewrites your prompts locally using Ollama before sending them to external AI providers.
The goal is simple:

- cleaner prompts
- better outputs
- less repetition
- full visibility into what gets sent
- local-first workflow

---

# Features

- Local prompt optimisation with Ollama
- Prompt flow visualisation
- Multi-provider AI support
- Tone injection system
- Local-only backend access
- Built-in Ollama model installer
- Streaming Ollama pull progress
- Automatic update checks
- Developer mode support
- Logging + diagnostics
- Basic API test suite

---

# Supported Providers

PromptForge currently supports:

- OpenAI
- Anthropic
- Google Gemini
- Groq
- Mistral
- xAI
- OpenRouter

You provide your own API keys.

---

# Architecture

```text
You
 ↓
PromptForge UI
 ↓
Local FastAPI backend
 ↓
Local Ollama optimisation
 ↓
External AI provider
```

The optimisation step happens locally before requests are sent externally.

---

# Requirements

## Required

- Python 3.9+
- Ollama
- Internet connection (for external providers)

## Recommended Ollama Model

```bash
ollama pull gemma3:4b
```

---

# Installation

## macOS / Linux

```bash
git clone https://github.com/FreddieSparrow/Promptforge.git
cd Promptforge

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
bash setup.sh
```

## Windows

```bat
git clone https://github.com/FreddieSparrow/Promptforge.git
cd Promptforge

python -m venv .venv
call .venv\Scripts\activate

pip install -r requirements.txt
setup.bat
```

---

# Launch

```bash
python main.py
```

Open:

```text
http://localhost:7474
```

---

# Ollama Setup

PromptForge expects Ollama at:

```text
http://localhost:11434
```

Check Ollama manually:

```bash
curl http://localhost:11434/api/tags
```

List installed models:

```bash
ollama list
```

Install a model:

```bash
ollama pull gemma3:4b
```

---

# Security

PromptForge is designed as a local-first application.

Current protections:

- localhost-only backend access
- request validation
- prompt size limits
- API key masking in UI
- logging for failures and diagnostics
- no external telemetry

Important:

- API keys are still stored locally in `config.json`
- this is suitable for local/private usage
- not intended for enterprise multi-user hosting

---

# Logging

Runtime logs are written to:

```text
promptforge.log
```

Useful for debugging:

- Ollama connectivity
- provider failures
- invalid settings
- blocked requests
- backend exceptions

---

# Tests

Run tests with:

```bash
pytest
```

Current tests include:

- settings endpoint
- providers endpoint
- tones endpoint
- prompt limit handling

---

# Configuration

Settings are stored in:

```text
config.json
```

Auto-created on first launch.

---

# Developer Notes

PromptForge is intentionally local-first.

This is not a cloud SaaS product.
The design prioritises:

- transparency
- local control
- simple architecture
- compatibility with Ollama
- provider flexibility

---

# Troubleshooting

## "Ollama unreachable"

Check:

```bash
ollama serve
```

Then:

```bash
curl http://localhost:11434/api/tags
```

---

## "Model missing"

Install a model:

```bash
ollama pull gemma3:4b
```

---

## Frontend says Ollama offline

Make sure Settings uses:

```text
http://localhost:11434
```

NOT:

```text
http://localhost:7474
```

7474 is PromptForge itself.

---

# Version

Current backend version:

```text
1.0.1
```

---

# License

Personal/open development project.
