"""Extraction LLM des champs candidat via LiteLLM (passerelle Ollama / OpenAI)."""
import json
import time

import httpx
from pydantic import ValidationError

from api.core.config import settings
from api.models.schemas import CandidatFields, DocumentExtraction, DocumentType, ParsedDocument

_SYSTEM_PROMPT = """Tu es un assistant d'extraction de données pour un établissement d'enseignement supérieur.
Extrais les champs demandés du document fourni.
Réponds UNIQUEMENT avec un objet JSON valide correspondant exactement au schéma.
Si un champ est absent du document, utilise null.
Ne déduis pas, n'invente pas de valeur."""

_FIELD_HINTS: dict[DocumentType, str] = {
    DocumentType.FORMULAIRE: "nom, prénom, date_naissance, adresse, email, téléphone, diplôme, établissement",
    DocumentType.IDENTITE: "nom, prénom, date_naissance, lieu_naissance, nationalité, numero_piece",
    DocumentType.RELEVE: "nom, prénom, diplôme, établissement, annee_obtention, moyenne",
    DocumentType.DOMICILE: "nom, prénom, adresse",
    DocumentType.INCONNU: "nom, prénom",
}

_SCHEMA_JSON = CandidatFields.model_json_schema()


def _build_prompt(doc: ParsedDocument) -> str:
    hints = _FIELD_HINTS.get(doc.doc_type, _FIELD_HINTS[DocumentType.INCONNU])
    schema_str = json.dumps(_SCHEMA_JSON, ensure_ascii=False, indent=2)
    text_snippet = doc.raw_text[:3000]
    return (
        f"Type de document : {doc.doc_type.value}\n"
        f"Champs à extraire : {hints}\n\n"
        f"Schéma JSON attendu :\n{schema_str}\n\n"
        f"Contenu du document :\n{text_snippet}\n\n"
        "JSON extrait :"
    )


async def extract_fields(doc: ParsedDocument) -> DocumentExtraction:
    prompt = _build_prompt(doc)
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }

    start = time.perf_counter()
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.litellm_base_url}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {settings.litellm_api_key}"},
        )
        resp.raise_for_status()
    latency_ms = (time.perf_counter() - start) * 1000

    data = resp.json()
    raw_content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    cost = data.get("_cost", 0.0) or _estimate_cost(usage, settings.llm_model)

    try:
        fields = CandidatFields.model_validate_json(raw_content)
    except (ValidationError, ValueError):
        # Tentative de nettoyage basique avant de retomber en mode dégradé
        cleaned = raw_content.strip().lstrip("```json").rstrip("```").strip()
        try:
            fields = CandidatFields.model_validate_json(cleaned)
        except (ValidationError, ValueError):
            fields = CandidatFields()

    return DocumentExtraction(
        doc_type=doc.doc_type,
        filename=doc.filename,
        fields=fields,
        raw_response=raw_content,
        extraction_latency_ms=latency_ms,
        model_used=data.get("model", settings.llm_model),
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        cost_usd=cost,
    )


def _estimate_cost(usage: dict, model: str) -> float:
    """Estimation grossière si LiteLLM ne retourne pas le coût."""
    if "gpt" in model.lower():
        input_cost = usage.get("prompt_tokens", 0) * 0.5 / 1_000_000
        output_cost = usage.get("completion_tokens", 0) * 1.5 / 1_000_000
        return round(input_cost + output_cost, 8)
    return 0.0
