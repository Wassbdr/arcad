# PREDI-Care

Application Streamlit de support a la decision clinique pour le cancer du rectum, concue dans le cadre du Hackathon A.R.CA.D 2026.

PREDI-Care simule une aide a la decision entre deux strategies therapeutiques:
- Chirurgie Radicale
- Surveillance active "Watch and Wait"

L'application utilise une architecture agentique multimodale (radiologie, biologie, coordination clinique), une interface medicale premium, des visualisations interactives Plotly, un module de discussion "Expert IA" et un export PDF de synthese.

## Avertissement Medical

Ce projet est une demonstration technique/prototype hackathon.
Il ne remplace en aucun cas l'avis d'un staff medical pluridisciplinaire ni les recommandations institutionnelles.
Toute decision clinique reelle doit etre validee par des professionnels qualifies.

## Fonctionnalites

- Pipeline unique v2:
  - une seule application Streamlit: app_v2
  - un seul moteur de decision: BrainEngineV2
  - fallback heuristique automatique si le LLM n'est pas disponible
- Simulation comparee des strategies:
  - chirurgie
  - watch and wait
- Mode cohorte:
  - import CSV robuste (validation + avertissements)
  - simulation batch
  - filtres/tri tableau
  - export CSV enrichi avec synthese par sous-cohorte
  - export PDF cohorte pagine par sous-cohorte
- Visualisations premium (Plotly):
  - Kaplan-Meier compare
  - comparaison des risques
  - explicabilite de type SHAP
- Export patient:
  - rapport PDF decisionnel individuel

## Architecture

Pipeline principal:
1. Saisie des variables cliniques dans la sidebar
2. Mapping des entrees vers format CRF
3. Appel LLM medical (si configure)
4. Fallback heuristique CRFSimulator si indisponible
5. Rendu UI:
  - comparaison des scenarios
  - graphiques de survie/risques
  - explicabilite
  - export PDF patient/cohorte

## Structure du projet

Architecture reorganisee (modulaire):

- app.py: point d'entree Streamlit
- src/predi_care/app_v2.py: orchestration UI unique
- src/predi_care/engine/brain_engine_v2.py: moteur de decision canonique
- src/predi_care/engine/patient_types.py: schema patient partage
- src/predi_care/engine/crf_mapper.py: mapping vers variables CRF
- src/predi_care/engine/crf_simulator.py: moteur heuristique de fallback
- src/predi_care/engine/llm_client.py: integration LLM medical
- src/predi_care/engine/mock_factory.py: generation de donnees de test
- src/predi_care/ui/comparative_ui.py: rendu compare des scenarios
- src/predi_care/ui/visuals_v2.py: visualisations Plotly v2
- src/predi_care/export/pdf_report.py: export PDF patient + cohorte
- src/predi_care/theme/style.css: theme medical premium
- docs/references/MEDICAL_LOGIC_REF.md: reference medico-logique
- docs/references/DESIGN_SYSTEM.md: charte UI/UX
- docs/VULGARISATION_IA_NON_TECH.md: explication complete pour profils non-tech IA
- docs/VULGARISATION_MEDECINE_NON_TECH.md: explication complete pour profils non-tech medical
- config/calibration_profile.template.yaml: profil de calibration a personnaliser
- tests/: suite de tests unitaires

## Prerequis

- Python 3.10+
- pip

## Installation rapide

1. Creer un environnement virtuel

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Installer les dependances

```bash
pip install -r requirements.txt
```

Version reproductible (verrouillee):

```bash
pip install -r requirements.lock
```

3. (Optionnel) Lancer les tests

```bash
pytest -q
```

## Lancer l'application

```bash
streamlit run app.py --server.headless true --server.port 8502
```

Puis ouvrir:
- http://localhost:8502

## Guide d'utilisation

1. Renseigner les donnees patient dans la sidebar:
   - stades cT/cN/cM
   - ACE pre-traitement et ACE actuel
   - residus tumoraux IRM
   - qualite imagerie
   - age, ECOG
2. Cliquer sur "Simuler"
3. Analyser les deux cartes de decision:
   - risque de recidive
   - confiance du modele
   - impact qualite de vie
4. Examiner les graphiques:
   - survie sans recidive par scenario
   - comparaison globale des risques
5. Exporter la synthese patient via "Telecharger Rapport PDF"
6. (Optionnel) Utiliser le mode cohorte pour import CSV et exports batch

## Details techniques

### BrainEngineV2
- entree unique: PatientInput
- conversion des donnees cliniques vers CRFInput
- tentative d'inference via LLM medical
- fallback heuristique sur CRFSimulator en cas d'echec

### Simulation et sortie
- comparaison chirurgie vs watch and wait
- metriques DFS, risques, qualite de vie, confiance
- rationale exploitable par l'UI et les exports

## XAI et SHAP

Le projet fournit des visualisations "SHAP-like" pour expliquer la decision.
Dans cette version hackathon:
- le calcul SHAP est simule a partir de contributions derivees des features
- les graphes respectent l'objectif d'explicabilite produit

Pour une version clinique de production, remplacer cette logique par:
- un modele ML valide
- un vrai calcul SHAP (Kernel/Tree/Linear selon le modele)
- une strategie de calibration et validation externe

## Personnalisation UI

Le rendu visuel est centralise dans src/predi_care/theme/style.css:
- palette medicale
- cartes de decision
- style des composants Streamlit
- responsive desktop/mobile

## Limitations actuelles

- Scores heuristiques en mode fallback
- Dependance a la qualite des donnees saisies/importees
- SHAP de type explicatif (pas un audit causal complet)
- Export PDF orienté demo (pas de template hospitalier officiel)

## Roadmap recommandee

- Integrer un modele ML entraine sur donnees reelles anonymisees
- Ajouter calibration, validation croisee et metriques cliniques (AUC, Brier, calibration curve)
- Brancher un LLM medical avec citations et garde-fous
- Ajouter authentification, audit trail, gestion RGPD/HDS
- Integrer FHIR/HL7 pour interoperabilite SIH
- Renforcer le PDF (template institutionnel, annexes graphiques, signature staff)

## Depannage

### Erreur: ModuleNotFoundError: streamlit

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Erreur: ModuleNotFoundError: plotly

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Warning Streamlit sur use_container_width

Le projet est migre vers width="stretch" pour compatibilite apres 2025-12-31.

## License

A definir selon les regles du hackathon et de l'equipe projet.

## Credits

Projet realise pour Hackathon A.R.CA.D 2026.
Equipe: Senior Full-Stack ML Engineering + UI/UX Medical Design.
