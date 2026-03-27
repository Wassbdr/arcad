#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate
python -m py_compile app.py src/predi_care/app_shell.py src/predi_care/engine/brain_engine.py src/predi_care/ui/visuals.py src/predi_care/chat/llm_chat.py
