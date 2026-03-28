# CRF_MAPPING

## Purpose
Mapping between:
- dataset v3 columns
- internal v4 Digital Twin fields
- e-CRF style variables

## Core Mapping Table

| Dataset v3 column | Internal field (`DataTwinProfile.core_clinical`) | e-CRF concept | Transform | Fallback |
|---|---|---|---|---|
| `baseline_cT` | `ct_stage` | ycT / post-neoadjuvant T | direct string | `cT3` |
| `baseline_cN` | `cn_stage` | ycN | direct string | `cN0` |
| `cM` | `cm_stage` | cM | direct string | `cM0` |
| `age_years` | `age` | age | numeric cast | `62` |
| `ecog_score` | `ecog` | ECOG/OMS | numeric cast | `1` |
| `asa_class` | `asa_score` | ASA | map `I/II/III/IV -> 1/2/3/4` | `2` |
| `cea_baseline_ng_ml` | `ace_baseline` | CEA baseline | numeric cast | `5.0` |
| `cea_current_ng_ml` | `ace_current` | CEA current | numeric cast | `3.0` |
| `residual_tumor_ratio_native` | `residual_tumor_ratio` | residual burden | `value * 100` | `30.0` |
| `restaging_residual_lesion_cm` | `residual_size_cm` | lesion size | numeric cast | derived from ratio (`/20`) |
| `restaging_mrTRG` | `trg` | mrTRG | clamp to `[1,5]` | derived from residual ratio |
| `restaging_endoscopy_response` | `clinical_response` | endoscopic response | `CCR/ICR/NCR -> complete/near_complete/partial` | derived from residual ratio |
| `imaging_quality` | `imaging_quality` | imaging quality | normalize to `Elevee/Moyenne/Basse` | `Moyenne` |
| `tumor_distance_from_anal_verge_cm` | `distance_marge_anale` | tumor height | numeric cast | `8.0` |
| `initial_restaging_weeks_post_crt` | `delay_weeks_post_rct` | restaging delay | numeric cast | `8` |
| `concomitant_chemotherapy` | `protocol_neoadjuvant` | protocol | direct string | `RCT standard` |
| `baseline_emvi` | `emvi` | EMVI | bool cast | `False` |
| `smoking_status` | `smoking` | tobacco status | `current -> True` else `False` | `False` |
| `diabetes` | `diabetes` | diabetes | bool cast | `False` |
| `albumin_g_l` | `albumin` | albumin | numeric cast | `40.0` |
| `hemoglobin_g_dl` | `hemoglobin` | hemoglobin | numeric cast | `13.0` |
| `msi_status` | `msi_status` | MSI/MMR | normalize label | `MSS/MSI-L` |
| `baseline_mri_crm_mm` | `crm_distance_mm` | CRM distance | numeric cast | `5.0` |
| derived from CRM distance | `crm_status` | CRM status | `<1 positive`, `<2 threatened`, else `negative` | derived |

## Provenance Rules
Each feature gets:
- `source`: `dataset`, `derived`, or `simulated`
- `quality`: `observed`, `imputed`, or `unknown`

When a critical field is missing:
- the engine imputes a deterministic fallback
- `missing_inputs` is updated
- provenance quality switches to `imputed`

## Calibration Guardrail
Columns starting with `prob_` or `p_` are treated as helper/debug probabilities and are excluded from label calibration targets.
