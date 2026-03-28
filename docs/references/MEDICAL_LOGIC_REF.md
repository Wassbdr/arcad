# MEDICAL_LOGIC_REF

## Scope
This document defines v4 prototype rules for PREDI-Care:
- tabular Digital Twin inference
- multi-agent orchestration
- deterministic safety envelope

The tool is clinical decision support, not an autonomous medical device.

## Hard Clinical Rules
- `watch_wait` is forbidden when `residual_size_cm > 2.0`.
- `watch_wait` is forbidden when `TRG > 2`.
- `cM1` forces `multidisciplinary`.
- `ECOG = 4` forces `multidisciplinary`.
- all probabilities must remain in `[0, 100]`.
- survival curves must be monotone non-increasing.
- on critical invariant breach, final recommendation is forced to `multidisciplinary`.

## Decision Thresholds
- Residual lesion:
  - `<= 1 cm`: favorable for organ preservation
  - `1-2 cm`: borderline
  - `> 2 cm`: hard block for watch and wait
- TRG:
  - `1-2`: favorable for watch and wait
  - `3`: intermediate, usually multidisciplinary discussion
  - `4-5`: unfavorable, surgery-centered strategy
- CRM:
  - `< 1 mm`: positive risk state
  - `1-2 mm`: threatened
  - `>= 2 mm`: negative
- ACE trend:
  - normalized or major drop: favorable
  - persistent elevation: unfavorable

## Complication Typology

### Surgery branch
- LARS syndrome
- anastomotic leak
- infectious complication
- urinary dysfunction
- stoma-related complication
- medical systemic complication

### Watch and Wait branch
- local regrowth risk
- conditional systemic relapse risk after regrowth
- surveillance burden
- anxiety burden linked to follow-up

Each reported risk must expose:
- value
- source (`dataset`, `simulated`, `derived`, `llm`)
- confidence
- supporting factors

## Multi-Agent Governance
Agents:
- Radiology
- Biology
- SurgeryRisk
- WatchWait
- Comorbidity
- EthicsRules
- Coordinator

Arbitration:
- low disagreement: automatic consensus
- medium disagreement: consensus + warning
- high disagreement: multidisciplinary escalation

Safety authority:
- EthicsRules and SafetyEnvelopeChecker can override recommendation.

## Fallback Policy
- primary runtime: OpenAI models
- secondary runtime: alternate LLM providers
- final fallback: heuristic-only mode
- runtime mode must be surfaced in UI (`openai`, `alt_llm`, `heuristic`)

## Counterfactual Standard
The explanation layer must provide actionable "minimal change" statements, e.g.:
- residual lesion reduction needed for watch and wait eligibility
- TRG threshold required to unlock watch and wait
- ACE reduction needed to improve watch and wait score
