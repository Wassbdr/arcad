# PREDI-Care explique simplement (version non-tech IA)

## A quoi sert ce projet ?
PREDI-Care aide les medecins a comparer deux options de prise en charge dans le cancer du rectum:
- Option 1: Chirurgie radicale
- Option 2: Surveillance active (Watch and Wait)

Le but n'est pas de remplacer le medecin, mais de lui donner une aide structuree, rapide et explicable.

## Idee generale en 30 secondes
Le logiciel lit plusieurs types d'informations patient:
- Donnees d'imagerie (stade cTNM, residu tumoral)
- Donnees biologiques (evolution du taux ACE)
- Donnees cliniques (age, etat general)

Ensuite, il:
1. estime un risque de recidive
2. compare les deux scenarios de soin
3. explique pourquoi il propose une orientation
4. affiche un niveau d'incertitude

## Comment le systeme "reflechit"
Le projet est decoupe en 3 "agents" (comme 3 experts):

1. Agent Radiologue
- Se concentre sur l'imagerie
- Evalue le risque local (ex: residu tumoral important)

2. Agent Biologiste
- Se concentre sur l'ACE
- Regarde si le marqueur baisse bien ou non

3. Agent Coordinateur
- Combine tout
- Applique des regles cliniques de securite
- Detecte les conflits (ex: imagerie rassurante mais biologie inquietante)
- Produit une recommandation finale + un niveau d'incertitude

## Ce que vous voyez a l'ecran
- A gauche: formulaire patient
- Au centre: 2 cartes de decision cote a cote
  - Risque estime
  - Confiance du modele
  - Impact qualite de vie
- En dessous:
  - Graphiques interactifs
  - Explication type SHAP (quels facteurs poussent la decision)
  - Chat Expert IA pour poser des questions
  - Export PDF du resume

## Pourquoi c'est "IA" sans etre une boite noire
Le projet donne:
- Une recommandation
- Une rationale textuelle
- Des alertes explicites
- Un score d'incertitude
- Des motifs de conflit inter-signaux

Donc on ne se contente pas d'un "oui/non": on explique la logique.

## Ce que veut dire "calibration" en langage simple
Calibration = verifier que les probabilites annoncees sont realistes.

Exemple:
- Si le modele dit "30% de risque" sur 100 patients comparables,
- alors environ 30 devraient reellement recidiver.

Si ce n'est pas le cas, on ajuste les seuils et les poids.

## Ce qu'il faut retenir sur la fiabilite
Le projet est:
- utile pour structurer la reflexion
- testable (tests automatiques)
- explicable

Mais:
- ce n'est pas encore un dispositif medical certifie
- les chiffres doivent etre recalibres avec des donnees cliniques reelles
- la decision finale reste medicale (RCP)

## Qui peut lire quoi dans le repo
- Pour comprendre le projet global: README
- Pour la logique metier medicale: docs/references/MEDICAL_LOGIC_REF.md
- Pour la calibration: docs/CALIBRATION_PLAYBOOK.md
- Pour le design: docs/references/DESIGN_SYSTEM.md

## Mini glossaire
- cTNM: systeme de stade tumoral
- ACE: marqueur biologique sanguin
- SHAP: methode d'explication de prediction
- Calibration: aligner probabilites predites et realite
- RCP: reunion de concertation pluridisciplinaire

## Message final
PREDI-Care est un copilote de decision: il accelere, structure et explique. Il n'impose pas la decision, il la rend plus lisible et argumentable.
