#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate
streamlit run app.py --server.port 8502
