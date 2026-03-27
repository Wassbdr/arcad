# PREDI-Care explique simplement (version non-tech medicale)

## Pourquoi ce document ?
Ce document est destine aux personnes qui ne viennent pas du monde medical (dev, design, data, jurys) pour comprendre le contexte clinique du projet.

## Le probleme clinique en termes simples
Dans certains cancers du rectum, une question importante se pose apres traitement initial:
- faut-il operer (chirurgie radicale) ?
- ou surveiller de tres pres (Watch and Wait) ?

Les deux options ont des benefices et des risques.

## Les 3 informations cles utilisees

1. Stade cTNM (imagerie)
- Indique l'extension de la maladie
- Plus le stade est eleve, plus le risque est generalement important

2. ACE (prise de sang)
- Marqueur biologique
- Une baisse est plutot rassurante
- Une valeur qui reste elevee ou remonte est un signal d'alerte

3. Residu tumoral IRM
- Estimation du tissu tumoral residuel
- Plus le residu est important, plus le risque de recidive peut etre eleve

## Que fait PREDI-Care concretement ?
Le logiciel:
1. recueille ces informations
2. calcule un risque de recidive estime
3. compare chirurgie vs surveillance
4. met en avant les alertes cliniques
5. signale s'il y a contradiction entre les signaux
6. affiche un niveau d'incertitude

## Pourquoi c'est utile pour l'equipe soignante
- Gain de temps pour synthese de dossier
- Vision structuree et comparable des scenarios
- Support de discussion en staff
- Traçabilite de la logique dans un resume PDF

## Ce que le logiciel ne fait PAS
- il ne remplace pas le medecin
- il ne pose pas un diagnostic a lui seul
- il ne se substitue pas aux recommandations institutionnelles
- il ne remplace pas la RCP

## Comment lire les resultats

### Recommandation
Orientation proposee selon les donnees entrees (chirurgie ou surveillance).

### Risque de recidive
Probabilite estimee, pas certitude individuelle.

### Incertitude
- Faible: signaux concordants
- Moyenne: quelques doutes
- Elevee: signaux contradictoires ou qualite de donnees limitee

### Conflits de donnees
Exemple typique:
- imagerie rassurante
- mais biologie defavorable

Dans ce cas, le systeme encourage la prudence et la reevaluation.

## Pourquoi il y a des graphiques
- Courbes de survie: visualiser les trajectoires possibles
- SHAP-style: montrer quels facteurs ont le plus influence la recommendation

## Pourquoi on parle de calibration
Un bon modele doit annoncer des probabilites credibles dans la vraie vie.
Si le modele dit 20%, il faut que cela corresponde a peu pres a la realite observee sur des patients comparables.

## Niveau de maturite actuel
- Prototype avance de hackathon
- Architecture propre et testee
- Explicabilite integree
- Necessite encore une calibration clinique multicentrique avant usage reel

## Pour les non-medecins: regle d'or
PREDI-Care n'est pas un "robot medecin".
C'est un outil d'aide a la decision, concu pour rendre la discussion clinique plus claire, plus argumentee et plus traçable.

## Ressources utiles du projet
- Vision globale: README
- Logique clinique detaillee: docs/references/MEDICAL_LOGIC_REF.md
- Plan de calibration: docs/CALIBRATION_PLAYBOOK.md
