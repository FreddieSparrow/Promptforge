# PromptForge

Free local AI prompt optimiser. Rewrites your prompts with on-device Gemma before sending to any AI provider.

## Quick Start

**macOS / Linux**
```bash
git clone https://github.com/FreddieSparrow/Promptforge.git
cd Promptforge
bash setup.sh
```

**Windows**
```
git clone https://github.com/FreddieSparrow/Promptforge.git
cd Promptforge
setup.bat
```

Opens at **http://localhost:7474**

## What it does

1. You type a rough prompt
2. Local Gemma (via Ollama) rewrites it to be clear, specific, and well-structured
3. Optionally inject a response tone (confident, technical, concise, etc.)
4. Sends the final prompt to whichever AI provider you choose
5. Shows all three versions — original, optimised, final — side by side

## Supported Providers

Add your API key in Settings for any of:
- OpenAI, Anthropic, Google Gemini, Groq, Mistral, xAI Grok, OpenRouter

## Requirements

- Python 3.9+
- Ollama (setup script installs this)
- `gemma3:4b` model (setup script pulls this)

## Config

Settings stored in `config.json` (auto-created on first run). API keys never leave your machine.

## Updates

Check [beaconapp.freddiesparrow.co.uk](https://beaconapp.freddiesparrow.co.uk) for new releases.
The app checks for updates automatically at startup.
