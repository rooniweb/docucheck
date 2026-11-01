"""Orchestration du pipeline complet pour un dossier."""
import time
from pathlib import Path

from api.models.schemas import DossierReport, DossierSubmit
from api.services import decision, docling_client, extractor, verifier


async def process_dossier(payload: DossierSubmit) -> DossierReport:
    start_total = time.perf_counter()

    # 1. Parsing Docling (parallélisable — asyncio.gather si besoin)
    parsed_docs = []
    total_docling_ms = 0.0
    total_pages = 0
    for file_path in payload.files:
        parsed = await docling_client.parse_document(file_path)
        parsed_docs.append(parsed)
        total_docling_ms += parsed.parse_latency_ms
        total_pages += max(1, len({e.page for e in parsed.elements}))

    # 2. Extraction LLM
    extractions = []
    total_llm_ms = 0.0
    total_cost = 0.0
    total_tokens = 0
    models_used: set[str] = set()

    for parsed in parsed_docs:
        extraction = await extractor.extract_fields(parsed)
        extractions.append(extraction)
        total_llm_ms += extraction.extraction_latency_ms
        total_cost += extraction.cost_usd
        total_tokens += extraction.prompt_tokens + extraction.completion_tokens
        if extraction.model_used:
            models_used.add(extraction.model_used)

    # 3. Vérification
    verification = verifier.verify(extractions)

    # 4. Décision TypeSafe Jev
    result = decision.decide(verification)

    total_ms = (time.perf_counter() - start_total) * 1000

    # Nom du candidat pour le rapport (priorité : formulaire > identité > premier doc)
    candidat_nom = _resolve_name(extractions)

    return DossierReport(
        dossier_id=payload.dossier_id,
        candidat_nom=candidat_nom,
        decision=result.decision,
        confidence=result.confidence,
        needs_human_review=result.needs_human_review,
        anomalies=verification.anomalies,
        extractions=extractions,
        verification=verification,
        total_latency_ms=round(total_ms, 1),
        docling_latency_ms=round(total_docling_ms, 1),
        llm_latency_ms=round(total_llm_ms, 1),
        total_cost_usd=round(total_cost, 8),
        total_tokens=total_tokens,
        models_used=list(models_used),
        pages_processed=total_pages,
    )


def _resolve_name(extractions) -> str | None:
    from api.models.schemas import DocumentType
    priority = [DocumentType.FORMULAIRE, DocumentType.IDENTITE, DocumentType.RELEVE]
    by_type = {e.doc_type: e for e in extractions}
    for t in priority:
        if t in by_type:
            f = by_type[t].fields
            if f.nom or f.prenom:
                return " ".join(filter(None, [f.prenom, f.nom]))
    return None
