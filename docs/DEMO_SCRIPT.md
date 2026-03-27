# Script de demonstration PREDI-Care (5 minutes)

Guide pour la presentation du hackathon A.R.CA.D 2026.

---

## Acte 1: Le Probleme (30 secondes)

> *"Le cancer du rectum pose un defi decisional majeur: quand la tumeur repond bien au traitement, doit-on operer systematiquement ou peut-on surveiller activement?*
>
> *PREDI-Care est une plateforme d'aide a la decision clinique qui utilise une architecture multi-agent pour guider ce choix therapeutique."*

---

## Acte 2: Architecture Multi-Agent (1 minute)

### Demonstration
1. Selectionner **"Candidat ideal Watch & Wait"** dans la sidebar
2. Cliquer sur **"Lancer Evaluation IA"**
3. Ouvrir l'expander **"Details par agent"**

### Points cles a mentionner
- **Agent Radiologue**: Analyse le stade cTNM, le residu tumoral et la qualite d'imagerie
- **Agent Biologiste**: Evalue la cinetique de l'ACE (marqueur tumoral)
- **Agent Coordinateur**: Fusionne les signaux, detecte les conflits, genere la recommandation

> *"Chaque agent apporte son expertise specialisee. Le coordinateur synthetise ces informations pour une decision robuste."*

---

## Acte 3: Explicabilite XAI (1 minute)

### Demonstration
1. Montrer les **metriques avec delta** (comparaison risques)
2. Faire defiler vers les graphiques **SHAP-like**
3. Mettre en evidence les alertes cliniques si presentes

### Points cles a mentionner
- Visualisation type SHAP pour comprendre l'impact de chaque variable
- Transparence totale: le clinicien voit *pourquoi* le modele recommande
- Conflits inter-agents detectes et explicites

> *"Pas de boite noire: chaque facteur est visible et quantifie."*

---

## Acte 4: Gestion des Conflits (1 minute)

### Demonstration
1. Selectionner **"Cas de conflit decisionnel"**
2. Relancer l'evaluation
3. Montrer le conflit detecte et l'incertitude elevee

### Points cles a mentionner
- Le systeme detecte quand les agents "ne sont pas d'accord"
- Niveau d'incertitude clairement affiche
- Recommandation de discussion en RCP renforcee

> *"Le systeme ne cache pas ses doutes. Il alerte le clinicien quand la decision merite une discussion approfondie."*

---

## Acte 5: Chat Expert (45 secondes)

### Demonstration
1. Dans le module **"Mode Discussion | Expert IA"**
2. Poser: *"Pourquoi privilegier la surveillance ici?"*
3. Montrer la reponse contextuelle

### Points cles a mentionner
- Questions-reponses sur la recommandation
- Explication pedagogique pour le patient ou l'equipe
- Extensible vers un LLM medical avec citations

---

## Acte 6: Export et Perspectives (45 secondes)

### Demonstration
1. Cliquer sur **"Exporter le resume PDF"**
2. Montrer le fichier genere

### Points cles a mentionner
- Export PDF pour le dossier patient
- Architecture modulaire (Docker-ready)
- Roadmap: integration FHIR/HL7, modele ML entraine, audit RGPD/HDS

> *"PREDI-Care est pret pour une integration hospitaliere. La prochaine etape: entrainement sur donnees reelles anonymisees."*

---

## Recapitulatif Final (15 secondes)

> *"PREDI-Care combine:*
> - *Architecture multi-agent*
> - *Explicabilite totale*
> - *Gestion intelligente de l'incertitude*
> - *Interface clinicien-friendly*
>
> *Merci de votre attention!"*

---

## Notes techniques pour les questions

- **Stack**: Python 3.10+, Streamlit, Plotly, ReportLab
- **Tests**: 16 tests unitaires (pytest)
- **Donnees**: Heuristiques calibrees (prototype), extensible vers ML
- **SHAP**: Simule pour la demo, remplacable par vrai SHAP apres entrainement
- **LLM Chat**: Mode simule, architecture prete pour API (OpenAI/Anthropic)
