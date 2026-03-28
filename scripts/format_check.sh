#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate
python -m py_compile \
	app.py \
	src/predi_care/app_v2.py \
	src/predi_care/engine/brain_engine_v2.py \
	src/predi_care/engine/crf_mapper.py \
	src/predi_care/engine/crf_simulator.py \
	src/predi_care/engine/llm_client.py \
	src/predi_care/engine/mock_factory.py \
	src/predi_care/engine/patient_types.py \
	src/predi_care/ui/comparative_ui.py \
	src/predi_care/ui/visuals_v2.py \
	src/predi_care/data/loader.py \
	src/predi_care/export/pdf_report.py
