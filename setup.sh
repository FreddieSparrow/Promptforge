#!/bin/bash
set -e

GREEN='\033[0;32m' YELLOW='\033[1;33m' RED='\033[0;31m' NC='\033[0m'
info()  { echo -e "${GREEN}[PromptForge]${NC} $1"; }
warn()  { echo -e "${YELLOW}[PromptForge]${NC} $1"; }
error() { echo -e "${RED}[PromptForge]${NC} $1"; exit 1; }

echo ""
echo "  PROMPTFORGE"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v python3 &>/dev/null; then
  error "Python 3 is required. Install from https://python.org"
fi
info "Python: $(python3 --version)"

if ! python3 -m venv --help &>/dev/null; then
  error "Python venv support is required. On Linux, install python3-venv."
fi

if [[ ! -d ".venv" ]]; then
  info "Creating virtual environment..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip --quiet

if ! command -v ollama &>/dev/null; then
  warn "Ollama not found."
  OS="$(uname -s)"
  if [[ "$OS" == "Darwin" ]]; then
    if command -v brew &>/dev/null; then
      info "Installing Ollama with Homebrew..."
      brew install ollama
    else
      warn "Install Ollama manually: https://ollama.com/download/mac"
    fi
  elif [[ "$OS" == "Linux" ]]; then
    warn "Install Ollama manually from https://ollama.com/download/linux or run their installer."
  else
    warn "Install Ollama manually: https://ollama.com"
  fi
fi

if command -v ollama &>/dev/null; then
  if ! curl -s http://localhost:11434/api/tags &>/dev/null; then
    info "Starting Ollama service..."
    ollama serve &>/dev/null &
    sleep 3
  fi
  info "Checking default model gemma3:4b..."
  if ! ollama list | grep -q "gemma3"; then
    info "Pulling gemma3:4b as the default starter model."
    ollama pull gemma3:4b || warn "Could not pull gemma3:4b. You can install a model later in Settings."
  fi
fi

info "Installing Python dependencies into .venv..."
python -m pip install -r requirements.txt --quiet || error "pip install failed"

info "Launching PromptForge at http://localhost:7474"
OS="$(uname -s)"
if [[ "$OS" == "Darwin" ]]; then
  (sleep 1.5 && open http://localhost:7474) &
elif [[ "$OS" == "Linux" ]]; then
  (sleep 1.5 && xdg-open http://localhost:7474 &>/dev/null || true) &
fi

python main.py
