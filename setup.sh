#!/bin/bash
set -e

GREEN='\033[0;32m' YELLOW='\033[1;33m' RED='\033[0;31m' NC='\033[0m'
info()  { echo -e "${GREEN}[PromptForge]${NC} $1"; }
warn()  { echo -e "${YELLOW}[PromptForge]${NC} $1"; }
error() { echo -e "${RED}[PromptForge]${NC} $1"; exit 1; }

echo ""
echo "  ██████╗ ██████╗  ██████╗ ███╗   ███╗██████╗ ████████╗"
echo "  ██╔══██╗██╔══██╗██╔═══██╗████╗ ████║██╔══██╗╚══██╔══╝"
echo "  ██████╔╝██████╔╝██║   ██║██╔████╔██║██████╔╝   ██║   "
echo "  ██╔═══╝ ██╔══██╗██║   ██║██║╚██╔╝██║██╔═══╝    ██║   "
echo "  ██║     ██║  ██║╚██████╔╝██║ ╚═╝ ██║██║        ██║   "
echo "  ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚═╝        ╚═╝   "
echo "  FORGE"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Python ────────────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  error "Python 3 is required. Install from https://python.org"
fi
info "Python: $(python3 --version)"

# ── pip ───────────────────────────────────────────────────────────────────────
if ! python3 -m pip &>/dev/null; then
  warn "pip not found — installing..."
  python3 -m ensurepip --upgrade || error "Failed to install pip"
fi

# ── Ollama ────────────────────────────────────────────────────────────────────
if ! command -v ollama &>/dev/null; then
  warn "Ollama not found — installing..."
  OS="$(uname -s)"
  if [[ "$OS" == "Darwin" ]]; then
    if command -v brew &>/dev/null; then
      brew install ollama
    else
      warn "Install Ollama manually: https://ollama.com/download/mac"
      warn "Then re-run this script."
    fi
  elif [[ "$OS" == "Linux" ]]; then
    curl -fsSL https://ollama.com/install.sh | sh
  else
    warn "Install Ollama manually: https://ollama.com"
  fi
fi

# ── Pull default starter model ────────────────────────────────────────────────
if command -v ollama &>/dev/null; then
  # Start ollama serve in background if not running
  if ! curl -s http://localhost:11434/api/tags &>/dev/null; then
    info "Starting Ollama service..."
    ollama serve &>/dev/null &
    sleep 3
  fi
  info "Pulling gemma3:4b as the default starter model (this may take a few minutes)..."
  info "You can install any other Ollama model from Settings inside the app."
  ollama pull gemma3:4b || warn "Could not pull gemma3:4b — open the app, go to Settings, and install a model from there."
fi

# ── Python deps ───────────────────────────────────────────────────────────────
info "Installing Python dependencies..."
cd "$SCRIPT_DIR"
python3 -m pip install -r requirements.txt --quiet || error "pip install failed"

# ── Launch ────────────────────────────────────────────────────────────────────
info "Launching PromptForge at http://localhost:7474"

OS="$(uname -s)"
if [[ "$OS" == "Darwin" ]]; then
  (sleep 1.5 && open http://localhost:7474) &
elif [[ "$OS" == "Linux" ]]; then
  (sleep 1.5 && xdg-open http://localhost:7474 &>/dev/null) &
fi

python3 main.py
