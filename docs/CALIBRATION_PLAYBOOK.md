# Calibration Playbook

## Objectif
Ce document liste tous les chiffres a collecter pour calibrer correctement PREDI-Care.
But: obtenir une probabilite de recidive fiable, exploitable en aide a la decision.

## 1) Variables brutes a collecter par patient

### Identifiants et contexte
- patient_id pseudonymise
- centre, periode de prise en charge
- date baseline (pre-therapeutique) et dates de suivi

### Clinique
- age
- sexe
- ECOG / performance status
- comorbidites majeures (indice simplifie)

### Radiologie (baseline et re-evaluations)
- cT, cN, cM
- score de qualite imagerie
- ratio de residu tumoral (%)
- date de chaque IRM

### Biologie
- ACE baseline (ng/mL)
- ACE intermediaire(s)
- ACE actuel (ng/mL)
- dates de dosage ACE

### Therapeutique
- strategie choisie (chirurgie vs watch-and-wait)
- date de decision
- traitements intermediaires (si applicables)

### Outcomes (ground truth)
- recidive locale (oui/non)
- recidive a 12/24/36 mois
- temps jusqu'a recidive (mois)
- metastases secondaires (oui/non)
- mortalite specifique (si disponible)

## 2) Chiffres minimaux de dataset pour une calibration solide

- n total recommande: >= 500 patients
- n minimum exploitable: >= 250 patients
- nombre d'evenements (recidives):
  - minimum absolu: >= 80
  - recommande: >= 120
- ratio evenements/non-evenements: eviter < 1:10
- couverture temporelle: >= 24 mois de suivi median

## 3) Chiffres de qualite des donnees a monitorer

- taux de valeurs manquantes par variable (%): cible < 5%
- taux de valeurs hors bornes (%): cible < 1%
- delai median entre IRM et ACE (jours): cible < 30
- coherence temporelle (baseline avant decision): cible 100%
- taux de labels outcome indetermines (%): cible < 3%

## 4) Metriques de discrimination a mesurer

- AUC-ROC global et IC95%
- AUC-PR global et IC95%
- Sensibilite, specificite, VPP, VPN
- F1-score (optionnel selon usage)

Cibles conseillees (pilotage):
- AUC-ROC >= 0.78
- AUC-PR >= 0.45

## 5) Metriques de calibration a mesurer (obligatoires)

- Brier score (global)
- Expected Calibration Error (ECE)
- Calibration slope
- Calibration intercept
- Courbe de calibration (deciles)
- O/E ratio (Observed/Expected)

Cibles conseillees:
- ECE <= 0.05
- Brier <= 0.18
- slope entre 0.90 et 1.10
- |intercept| <= 0.10

## 6) Points operatoires cliniques a figer avec le staff

### Pour favoriser la surveillance (rule-out recidive)
- sensibilite minimale: >= 0.95
- VPN minimale: >= 0.95

### Pour favoriser la chirurgie (rule-in risque)
- specificite minimale: >= 0.80
- VPP minimale a definir selon prevalence locale

## 7) Stratifications obligatoires (equite/performance)

Calculer toutes les metriques par sous-groupes:
- age: <50, 50-65, >65
- ECOG: 0-1, 2, >=3
- stades: cT1-2, cT3, cT4
- nodal: cN0, cN1, cN2
- centres hospitaliers (si multicentrique)

Alerte si derive > 0.05 d'ECE ou > 0.07 d'AUC entre sous-groupes.

## 8) Chiffres de drift a surveiller en production pilote

- variation prevalence recidive (delta %)
- delta moyenne ACE baseline/actuel
- delta distribution cT/cN/cM
- PSI par variable cle (>0.2 = alerte, >0.3 = critique)
- delta ECE et Brier vs reference

## 9) Plan de calibration recommande

1. Split temporel (train ancien / test recent)
2. Entrainer modele brut
3. Comparer methodes de calibration:
   - Platt
   - Isotonic
   - Beta calibration
4. Choisir la methode avec meilleur compromis ECE + Brier + courbe lisse
5. Verrouiller seuils cliniques avec validation staff
6. Re-evaluer trimestriellement

## 10) Format de tableau de collecte (colonnes minimales)

- patient_id
- center_id
- baseline_date
- ct_stage
- cn_stage
- cm_stage
- residual_tumor_ratio
- imaging_quality
- ace_baseline
- ace_current
- ace_drop_pct
- age
- ecog
- decision_strategy
- recurrence_12m
- recurrence_24m
- recurrence_36m
- time_to_recurrence_months

## 11) Checklist sprint calibration (actionnable)

- Definir cohorte retrospective cible (n, centres, periode)
- Verifier qualite et completude des variables cle
- Construire baseline model + calibration methods
- Produire tableau comparatif des metriques
- Valider thresholds operatoires en staff clinique
- Integrer profile dans config/calibration_profile.template.yaml
- Documenter version model + date + metriques dans changelog

## 12) Gouvernance

- Toute mise a jour de seuils doit etre versionnee
- Conserver trace: donnees utilisees, metriques, date, responsable validation
- Toujours afficher niveau d'incertitude et alertes cliniques dans l'UI et le PDF
