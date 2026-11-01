# Données synthétiques

Ce répertoire contiendra 12 dossiers d'inscription 100 % fictifs pour les tests d'évaluation.

## Structure d'un dossier

```
D01_conforme/
├── formulaire.pdf      # Formulaire d'inscription rempli
├── cni.pdf             # Pièce d'identité (nom fictif, numéro fictif)
├── releve.pdf          # Relevé de notes / diplôme
└── quittance.pdf       # Justificatif de domicile
```

## Génération

Les PDFs seront générés avec `reportlab` (PDFs natifs) et un scan simulé (image + re-encodage PDF)
pour reproduire des conditions réelles. Aucune donnée personnelle réelle n'est utilisée.

Script de génération : `scripts/generate_synthetic.py` (à venir).

## Cas couverts

| ID  | Dossier | Anomalie attendue |
|-----|---------|-------------------|
| D01 | Conforme | — |
| D02 | Identité manquante | MISSING_PIECE_IDENTITE |
| D03 | Nom incohérent | MISMATCH_NOM |
| D04 | Date naissance incohérente | MISMATCH_DATE_NAISSANCE |
| D05 | Année diplôme future | INVALID_ANNEE_DIPLOME |
| D06 | Domicile manquant | MISSING_JUSTIFICATIF_DOMICILE |
| D07 | Scan dégradé | Warning lisibilité |
| D08 | Adresse incohérente | MISMATCH_ADRESSE |
| D09 | Deux pièces manquantes | 2 erreurs complétude |
| D10 | Prénom incohérent | MISMATCH_PRENOM |
| D11 | Conforme (via API) | — |
| D12 | Formulaire + nom incohérent | 2 anomalies |
