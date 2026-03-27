# DESIGN_SYSTEM

## Vision
Charte UI/UX "Medical Premium" pour PREDI-Care:
- Sobre
- Rassurante
- Lisible en contexte clinique
- Optimisee pour usage desktop et tablette en staff

## Fondamentaux visuels

### Palette
- Primary Medical Blue: #005EB8
- Background Light: #F8FAFC
- White Surface: #FFFFFF
- Primary Text Slate: #2D3748
- Success Accent: #2F855A
- Warning Accent: #B7791F
- Border Soft: #E2E8F0

Principes:
- Fond clair non agressif
- Contraste eleve pour la lisibilite
- Couleurs d'alerte reservees aux signaux cliniques importants

### Typographie
- Familles: Inter, Roboto, sans-serif
- Hierarchie:
  - H1: 30-34 px, semi-bold/bold
  - H2: 22-26 px, semi-bold
  - H3: 18-20 px, medium/semi-bold
  - Body: 15-16 px, regular
  - Caption: 12-13 px
- Line-height:
  - Titres: 1.2-1.3
  - Corps: 1.5-1.6

## Composants principaux

### Header medical
- Bandeau principal avec:
  - titre produit
  - sous-titre de mission clinique
  - badges des agents (Radiologue, Biologiste, Coordinateur)
- Style:
  - fond blanc avec legere profondeur
  - bordure fine bleue
  - halo subtil decoratif

### Sidebar (saisie structuree)
- Inputs ordonnes par logique clinique:
  1) staging cTNM
  2) biologie ACE
  3) imagerie residuelle
  4) facteurs patient
- Boutons:
  - "Charger un patient virtuel"
  - "Lancer Evaluation IA"

### Decision Cards
- Deux cartes cote a cote:
  - Scenario A: Chirurgie radicale
  - Scenario B: Watch and Wait
- Contenu:
  - risque de recidive
  - confiance modele
  - impact qualite de vie
  - courbe de survie
  - graphique explicatif XAI
- Style:
  - coins arrondis 12 px
  - ombre douce
  - bordure claire
  - labels scenario discrets mais visibles

### Graphiques
- Bibliotheque: Plotly
- Exigences:
  - mode clair
  - axes explicites
  - unite affichee
  - legende concise
- Graphes principaux:
  - courbes de survie comparees
  - bar chart de risques
  - SHAP-style force/summary

### Module chat Expert IA
- Zone conversation lisible avec bulles sobres
- Input unique en bas, prompt contextualise
- Reponses courtes, claires, justifiees

### Export PDF
- Bouton principal dans la section synthese
- Rapport compact:
  - recommendation
  - score global
  - details par scenario
  - rationale

## Regles d'ergonomie medicale
- Prioriser les informations critiques en haut d'ecran
- Eviter la surcharge cognitive
- Utiliser des labels explicites (pas d'abreviations non definies)
- Assurer la coherence des terminologies entre UI et rapport PDF
- Maintenir un temps de lecture court pour la prise de decision

## Motion et feedback
- Animations discretes uniquement
- Feedback immediat au clic des actions majeures
- Pas d'effets distrayants

## Accessibilite
- Contraste cible >= WCAG AA
- Focus visible clavier sur boutons et champs
- Taille de police lisible sans zoom
- Zones cliquables confortables

## Tokens UI recommandes
- Border radius principal: 12 px
- Shadow soft: 0 8px 24px rgba(0, 94, 184, 0.08)
- Shadow card: 0 4px 14px rgba(45, 55, 72, 0.08)
- Spacing base: 8 px
- Espacement de section: 24-32 px

## Mapping implementation
- Style centralise dans src/predi_care/theme/style.css
- Injection CSS dans app.py via st.markdown(<style>...</style>)
- Composants metier rendus par fonctions Python dediees

## Checklist de revue design
- La page est-elle compréhensible en moins de 10 secondes ?
- Les deux scenarios sont-ils comparables sans effort ?
- Les informations critiques sont-elles visibles sans scroll excessif ?
- Les graphes expliquent-ils la decision sans ambiguite ?
- Le rendu inspire-t-il confiance en contexte hospitalier ?
