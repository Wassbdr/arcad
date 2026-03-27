# MEDICAL_LOGIC_REF

## Objet
Reference de logique medicale pour PREDI-Care (prototype hackathon) sur le dilemme therapeutique du cancer du rectum:
- Chirurgie radicale
- Surveillance active Watch and Wait

Cadre de travail:
- Inspiration des pratiques de discussion pluridisciplinaire type GRECCAR
- Donnees cles: cTNM, cinetique ACE, residu tumoral IRM
- Usage: support a la decision, non substitut au jugement clinique

## Variables cliniques et biologiques clefs

### 1) Stade cTNM
- cT:
  - cT1-cT2: risque local plutot faible a intermediaire
  - cT3: risque intermediaire a eleve
  - cT4: risque eleve
- cN:
  - cN0: favorable
  - cN1-cN2: aggravation du risque
- cM:
  - cM0: pas de metastase detectee
  - cM1: haut risque, discussion therapeutique differente

Regle simplifiee de vigilance:
- Alerte forte si cT4, cN2, ou cM1

### 2) Cinetique ACE (CEA)
Unite: ng/mL

Seuils de reference proposes pour le prototype:
- ACE <= 5 ng/mL: zone rassurante
- ACE > 5 ng/mL: alerte biologique
- ACE >= 10 ng/mL: alerte renforcee

Dynamique:
- Baisse >= 50-60% apres traitement: favorable
- Baisse 30-50%: intermediaire
- Baisse < 30% ou hausse: signal defavorable

Regle simplifiee de vigilance:
- Alerte forte si ACE actuel > 5 ng/mL et baisse < 30%

### 3) Residu tumoral IRM
Mesure simplifiee en ratio de residu tumoral (%)

Seuils proposes:
- < 10%: reponse tres favorable
- 10-30%: reponse partielle acceptable
- 30-50%: residu significatif
- > 50%: residu important, risque eleve

Regle simplifiee de vigilance:
- Alerte forte si residu tumoral > 30%

## Matrice de risque (prototype)

### Risque faible
Conditions typiques:
- cT1-cT2, cN0, cM0
- ACE <= 5 et en baisse significative
- Residu tumoral faible (< 10-20%)

Orientation possible:
- Surveillance active discutee si concordance clinico-radiobiologique

### Risque intermediaire
Conditions typiques:
- cT3 ou cN1
- ACE limite ou baisse partielle
- Residu tumoral 20-40%

Orientation possible:
- Decision individualisee en RCP selon comorbidites, preference patient, qualite imagerie

### Risque eleve
Conditions typiques:
- cT4, cN2, cM1, ou discordance majeure des signaux
- ACE > 5 persistant / en hausse
- Residu tumoral > 30-50%

Orientation possible:
- Tendance vers strategie de controle local maximal (chirurgie) ou adaptation oncologique selon contexte

## Regles de fusion multi-agent recommandees

### Agent Radiologue
Entrées:
- cT, cN, cM
- ratio de residu tumoral

Sorties:
- score_radiologique (0-1)
- confiance_radiologique

### Agent Biologiste
Entrées:
- ACE baseline
- ACE actuel

Sorties:
- score_biologique (0-1)
- dynamique (favorable, intermediaire, defavorable)

### Agent Coordinateur
Fonctions:
- fusionner score_radiologique + score_biologique + variables cliniques
- detecter les conflits de donnees
- produire recommandation finale et justification

Politique de gestion des conflits:
- Si conflit fort (ex: IRM favorable mais ACE en hausse persistante), marquer "incertitude elevee" et recommander reevaluation rapprochee
- Si cM1, prioriser la logique oncologique globale et diminuer la confiance du mode "watch and wait"

## Niveau de confiance suggere
- Eleve: signaux concordants et complets
- Moyen: discordance mineure ou donnee limite
- Faible: discordance majeure, donnees manquantes, ou qualite imagerie insuffisante

## Limites et gouvernance
- Reference simplifiee pour prototype hackathon
- Ne remplace pas les recommandations officielles, protocoles locaux, ni l'avis d'une RCP
- Toute recommendation doit etre revue et validee par cliniciens experts

## Sources de validation interne a prevoir
- Relecture par experts cliniques du projet
- Ajustement des seuils selon retours terrain
- Traçabilite des changements de logique dans le repo
