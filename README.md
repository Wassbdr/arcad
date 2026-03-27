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

- Architecture Multi-Agent:
  - Agent Radiologue: interprete cTNM, residu tumoral, qualite d'imagerie
  - Agent Biologiste: analyse la cinetique ACE
  - Agent Coordinateur: fusionne les signaux multimodaux et genere une recommandation
    - regles explicites ACE/TNM/residu tumoral
    - gestion des conflits inter-agents et niveau d'incertitude
- Moteur de risque:
  - simulation de probabilite de recidive
  - comparaison des risques par scenario
- UX "Medical Minimalist":
  - header clinique moderne
  - sidebar de saisie structuree
  - deux cartes de decision cote a cote
- Visualisation interactive (Plotly):
  - courbes de survie sans recidive
  - bar chart de comparaison des risques
- XAI (explicabilite):
  - visualisations de type SHAP Force et SHAP Summary (mode simule)
- Mode Discussion:
  - chat "Expert IA" sur la recommandation
- Export:
  - generation d'un resume PDF patient
- Donnees de test:
  - generateur de patients virtuels et cohortes mock

## Architecture

Pipeline principal:
1. Saisie des variables cliniques dans la sidebar
2. Agent Radiologue -> score de risque local et confiance
3. Agent Biologiste -> score biologique et dynamique ACE
4. Agent Coordinateur -> probabilite de recidive + comparaison des scenarios
5. Rendu UI:
   - Decision Cards
   - graphiques de survie
   - explicabilite XAI
   - chat expert
   - export PDF

## Structure du projet

Architecture reorganisee (modulaire):

- app.py: point d'entree Streamlit
- src/predi_care/app_shell.py: orchestration UI complete
- src/predi_care/engine/brain_engine.py: logique multi-agent et fusion
- src/predi_care/engine/mock_factory.py: generation de donnees de test
- src/predi_care/ui/visuals.py: visualisations Plotly + SHAP-style
- src/predi_care/chat/llm_chat.py: facade chat expert (simule/API)
- src/predi_care/theme/style.css: theme medical premium
- docs/references/MEDICAL_LOGIC_REF.md: reference medico-logique
- docs/references/DESIGN_SYSTEM.md: charte UI/UX
- docs/CALIBRATION_PLAYBOOK.md: guide complet de calibration
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
2. Cliquer sur "Lancer Evaluation IA"
3. Analyser les deux cartes de decision:
   - risque de recidive
   - confiance du modele
   - impact qualite de vie
4. Examiner les graphiques:
   - survie sans recidive par scenario
   - comparaison globale des risques
5. Interroger le module "Mode Discussion | Expert IA"
6. Exporter la synthese via "Exporter le resume PDF"

## Details techniques

### Agent Radiologue
Entrées principales:
- cT, cN, cM
- ratio de residu tumoral
- qualite d'imagerie

Sorties:
- local_recurrence_risk
- radiology_confidence
- resume radiologique

### Agent Biologiste
Entrées principales:
- ACE baseline
- ACE actuel

Sorties:
- bio_risk
- pourcentage de baisse ACE
- resume biologique

### Agent Coordinateur
Fusion des sorties agents + facteurs cliniques (age, ECOG) pour produire:
- probabilite globale de recidive
- recommandation finale
- rationale textuelle
- score d'incertitude (Faible/Moyenne/Elevee)
- detection de conflits de donnees et motifs associes
- alertes cliniques (ACE, TNM, residu tumoral)
- simulation des scenarios:
  - risque chirurgie
  - risque watch and wait
  - impact qualite de vie
- contributions explicatives type SHAP-like

### Module Chat Expert
- Service dedie dans src/predi_care/chat/llm_chat.py
- Mode actuel: simulated
- Extension prevue: branchement API LLM (mode api)

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

- Scores et coefficients heuristiques (prototype)
- SHAP simule (non issu d'un modele entraine)
- Chat base sur une logique reglee par regles
- Export PDF minimaliste (sans template clinique officiel)

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
