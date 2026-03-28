# Templates eCRF GRECCAR - Documentation

Ce dossier contient les templates (formulaires vides) des études cliniques GRECCAR.

## 📁 Contenu

### Études Analysées

| Fichier | Étude | Année | Format | Status |
|---------|-------|-------|--------|--------|
| `11JLE-Greccar6_items-ecrf_20120911.xls` | GRECCAR 6 | 2012 | Excel | ✅ Analysé |
| `GRECCAR9_eCRF_14122023_v5.pdf` | GRECCAR 9 | 2023 | PDF | ✅ Analysé |
| `GRECCAR12-CO-v9.0-20220707_Suivi Vital et Oncologique au 09.06.2022.pdf` | GRECCAR 12 | 2022 | PDF | ✅ Analysé |
| `NORAD01ecrfv1 16112018.xls` | NORAD 01 | 2018 | Excel | ⚪ Non analysé |
| `Cahier d'observation Greccar2 - v 3.0 du 19.03.2013.pdf` | GRECCAR 2 | 2013 | PDF | ⚪ Non analysé |

### Autres Documents

| Fichier | Type | Contenu |
|---------|------|---------|
| `colo-dictionary-t20241011.pdf` | Dictionnaire | Définitions variables colorectales |
| `ATT00001.htm` | Email | Correspondance projet GRECCAR |
| `france2030_PEPR_SanteNum_AAP_Lettre_Intention_PREDI_CARE_VF2-1.pdf` | Administratif | Lettre intention projet |
| `COTTE_EDDY_2025_AAP-Messidore-Lettre_dossier192334_*.pdf` | Administratif | Dossier financement |

## 📊 Résultats de l'Analyse

### Variables Critiques Identifiées

**GRECCAR 6** (37 variables clés)
- TNM complet (ypT0-4, N0-2, M0-1)
- Performance ECOG 0-1
- Régression tumorale (grades)
- Imagerie (IRM, écho-endoscopie)
- ❌ Pas de marqueurs biologiques (ACE)

**GRECCAR 9** (86+ variables)
- TNM complet (T1-4, N0-2, M0-1)
- ✅ **ACE (baseline + suivi 3/6 mois)**
- ✅ **CA 19.9**
- ✅ **Évaluation récidive structurée**
- Performance ECOG 0-2
- IRM pelvienne

**GRECCAR 12** (233+ variables)
- TNM détaillé (T3 subdivisé a/b/c/d)
- ✅ **ACE (ng/ml)**
- ✅ **CA 19.9**
- ✅ **Suivi vital et oncologique**
- Performance ECOG 0-4
- IRM pelvienne + échoendoscopie

### Score de Couverture PREDI-Care

| Variable | GRECCAR 6 | GRECCAR 9 | GRECCAR 12 |
|----------|-----------|-----------|------------|
| TNM (T/N/M) | ✅ | ✅ | ✅ |
| ACE | ❌ | ✅ | ✅ |
| Résidu tumoral | ✅ | ✅ | ✅ |
| Imagerie | ✅ | ✅ | ✅ |
| Age | ✅ | ✅ | ✅ |
| Performance ECOG | ✅ | ✅ | ✅ |

**Score Global** : **9/9 variables = 100%** ✅ (études récentes)

## 📚 Documentation Complète

Voir le dossier parent `/docs/` pour :
- `GRECCAR_COMPARATIVE_ANALYSIS.md` - Analyse comparative complète
- `GRECCAR6_COVERAGE_REPORT.md` - Rapport détaillé GRECCAR 6
- `FINAL_SUMMARY.md` - Résumé exécutif
- `DATA_INTEGRATION_PLAN.md` - Plan d'intégration données

## 🎯 Utilisation

Ces templates servent à :
1. ✅ **Valider** le modèle de données PREDI-Care
2. ✅ **Documenter** les standards GRECCAR
3. ✅ **Préparer** l'intégration futures données réelles
4. ✅ **Calibrer** le générateur de données synthétiques

## ⚠️ Note Importante

Ces fichiers sont des **templates vides** (formulaires), pas des données patients.
Ils documentent la **structure** des études GRECCAR, pas les résultats.

## 📖 Références

- [GRECCAR Studies](https://www.greccar.fr/)
- Documentation complète : `/docs/`
- Métadonnées extraites : `/data/metadata/`
