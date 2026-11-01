# DocuCheck — Contrôle automatisé de dossiers d'inscription

[![CI](https://github.com/rooniweb/docucheck/actions/workflows/ci.yml/badge.svg)](https://github.com/rooniweb/docucheck/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Pipeline IA de bout en bout pour contrôler des dossiers d'inscription dans un établissement d'enseignement supérieur : parsing documentaire (PDF natifs + scannés), extraction LLM structurée, vérification par règles métier, décision confiance-seuil et rapport d'anomalies.

---

## Schéma du flux

```
                ┌─────────┐
  PDF × N  ──► │  n8n    │  webhook — dépose le dossier
                └────┬────┘
                     │
                     ▼
          ┌──────────────────┐
          │  Docling Serve   │  OCR + extraction structurée
          │  (Docker, REST)  │  → JSON : texte, tableaux, positions
          └────────┬─────────┘
                   │  ParsedDocument (par pièce)
                   ▼
          ┌──────────────────┐
          │   Classifier     │  identification du type de pièce
          │   (règles Python)│  formulaire / identité / relevé / domicile
          └────────┬─────────┘
                   │
                   ▼
          ┌──────────────────┐
          │    Extractor     │  LLM via LiteLLM
          │  (LLM + Pydantic)│  → CandidatFields validé
          └────────┬─────────┘   (nom, prénom, dob, diplôme…)
                   │
                   ▼
          ┌──────────────────┐
          │    Verifier      │  règles Python
          │                  │  complétude + cohérence inter-pièces
          └────────┬─────────┘
                   │
                   ▼
          ┌──────────────────┐
          │  TypeSafe Jev    │  décision pondérée
          │  (moteur règles) │  conforme / incomplet / à vérifier
          └────────┬─────────┘  + score de confiance [0,1]
                   │
          score < 0.80 ──► revue humaine (n8n routing)
                   │
                   ▼
          ┌──────────────────┐
          │     Rapport      │  anomalies (pièce + page + champ)
          │                  │  + métriques : coût, latence, modèle
          └──────────────────┘
```

---

## Lancement en une commande

```bash
cp .env.example .env
docker compose up
```

| Service       | URL locale                   | Usage                                |
|---------------|------------------------------|--------------------------------------|
| API FastAPI   | http://localhost:8000/docs   | Soumettre un dossier, lire le rapport|
| n8n           | http://localhost:5678        | Webhook + routage                    |
| Open WebUI    | http://localhost:3000        | Interroger les dossiers en langage naturel |
| Docling UI    | http://localhost:5001        | Tester le parsing seul               |
| LiteLLM       | http://localhost:4000        | Passerelle LLM                       |

> **GPU (optionnel)** : décommentez la section `deploy.resources` dans `docker-compose.yml` pour Ollama, et la section `vllm` dans `litellm/config.yaml` pour vLLM.

---

## Données synthétiques

Le jeu de test comprend 12 dossiers entièrement fictifs dans `data/synthetic/`, couvrant :

| Cas | Description | Anomalie attendue |
|-----|-------------|-------------------|
| D01 | Dossier parfait | Aucune |
| D02 | Pièce d'identité manquante | `MISSING_PIECE_IDENTITE` |
| D03 | Nom différent entre formulaire et CNI | `MISMATCH_NOM` |
| D04 | Date de naissance incohérente | `MISMATCH_DATE_NAISSANCE` |
| D05 | Relevé avec année future | `INVALID_ANNEE_DIPLOME` |
| D06 | Justificatif de domicile absent | `MISSING_JUSTIFICATIF_DOMICILE` |
| D07 | PDF scanné peu lisible (OCR dégradé) | Warning lisibilité |
| D08 | Adresse différente formulaire/domicile | `MISMATCH_ADRESSE` |
| D09 | Deux pièces manquantes | Deux erreurs complétude |
| D10 | Prénom différent entre pièces | `MISMATCH_PRENOM` |
| D11 | Dossier parfait (modèle API) | Aucune — coût > 0 |
| D12 | Formulaire illisible + nom incohérent | Deux anomalies |

---

## Résultats d'évaluation

> *Mesures sur le jeu synthétique — à compléter après construction.*

### Classement des dossiers

| Métrique | Ollama/Mistral | OpenAI GPT-4o-mini |
|----------|----------------|--------------------|
| Taux de bonne décision | — | — |
| Précision extraction nom | — | — |
| Rappel anomalies | — | — |

### Coût et latence (par dossier, 4 pièces)

| Métrique | Ollama local | GPT-4o-mini API |
|----------|-------------|-----------------|
| Latence totale | — | — |
| Latence Docling / page | — | — |
| Coût tokens | 0 € | — |

*Les colonnes seront remplies avec les mesures réelles lors de la mise en service.*

---

## Stack technique

| Couche | Technologie | Rôle |
|--------|-------------|------|
| Parsing | [Docling Serve](https://github.com/DS4SD/docling) | PDF natifs + OCR, JSON structuré |
| LLM gateway | [LiteLLM](https://github.com/BerriAI/litellm) | Bascule Ollama ↔ OpenAI, suivi coûts |
| LLM local | [Ollama](https://ollama.com/) + Mistral 7B | Inférence sans GPU obligatoire |
| LLM cloud | OpenAI GPT-4o-mini | Fallback et comparatif |
| Orchestration | [n8n](https://n8n.io/) | Webhook, routing, alertes |
| API | FastAPI + Pydantic v2 | Service Python, schémas validés |
| Décision | TypeSafe Jev | Score de confiance pondéré |
| UI NL | [Open WebUI](https://github.com/open-webui/open-webui) | Interrogation en langage naturel |
| Infra | Docker Compose | Déploiement local + Linux |
| CI | GitHub Actions | Tests + build image |

---

## Tests

```bash
# Sans Docker
pip install -r api/requirements.txt pytest pytest-asyncio
pytest tests/ -v

# Dans le conteneur
docker compose exec api pytest tests/ -v
```

Les tests unitaires (`tests/test_verifier.py`, `tests/test_decision.py`) ne nécessitent **ni LLM ni Docling** : ils testent les règles Python pures sur des fixtures en mémoire.

---

## Limites connues

- **vLLM** : non testé (machine de dev sans GPU NVIDIA). La configuration est documentée dans `litellm/config.yaml` ; l'activation nécessite une machine avec driver CUDA.
- **Docling OCR** : la précision dépend de la qualité du scan. Les PDFs très dégradés (< 150 dpi) peuvent produire des extractions partielles.
- **Données synthétiques uniquement** : aucune donnée réelle n'a été utilisée.
- **Open WebUI** : l'interrogation NL des dossiers traités suppose une intégration RAG (pipeline à connecter) — non finalisée dans cette version.

---

## Structure du projet

```
docucheck/
├── api/                  # Service FastAPI
│   ├── core/config.py    # Paramètres (pydantic-settings)
│   ├── models/schemas.py # Types Pydantic
│   ├── routers/          # Endpoints REST
│   └── services/         # Pipeline : docling_client, extractor, verifier, decision
├── litellm/config.yaml   # Passerelle LLM (Ollama + OpenAI)
├── data/synthetic/       # Dossiers fictifs pour les tests
├── tests/                # Tests pytest (règles + décision)
├── .github/workflows/    # CI (tests + build Docker)
├── docker-compose.yml    # Stack complète
└── .env.example
```

---

## Licence

MIT — voir [LICENSE](LICENSE).
