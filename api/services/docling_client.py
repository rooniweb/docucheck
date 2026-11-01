"""Client HTTP pour Docling Serve (conteneur Docker, REST API)."""
import time
from pathlib import Path

import httpx

from api.core.config import settings
from api.models.schemas import DoclingElement, DocumentType, ParsedDocument


_KEYWORD_MAP: dict[DocumentType, list[str]] = {
    DocumentType.FORMULAIRE: ["formulaire", "inscription", "candidature", "demande"],
    DocumentType.IDENTITE: ["carte nationale", "passeport", "identité", "cni", "cnib"],
    DocumentType.RELEVE: ["relevé", "notes", "baccalauréat", "diplôme", "moyenne", "bulletin"],
    DocumentType.DOMICILE: ["domicile", "résidence", "quittance", "loyer", "facture", "edf", "orange"],
}


def _classify_type(text: str) -> DocumentType:
    text_lower = text.lower()
    scores: dict[DocumentType, int] = {t: 0 for t in DocumentType if t != DocumentType.INCONNU}
    for doc_type, keywords in _KEYWORD_MAP.items():
        scores[doc_type] = sum(1 for kw in keywords if kw in text_lower)
    best = max(scores, key=lambda t: scores[t])
    return best if scores[best] > 0 else DocumentType.INCONNU


async def parse_document(file_path: str | Path) -> ParsedDocument:
    """Envoie un PDF à Docling Serve et retourne le document structuré."""
    path = Path(file_path)
    start = time.perf_counter()

    async with httpx.AsyncClient(timeout=120) as client:
        with open(path, "rb") as f:
            resp = await client.post(
                f"{settings.docling_base_url}/v1/convert/file",
                files={"files": (path.name, f, "application/pdf")},
                data={"options": '{"ocr": true, "table_mode": "accurate"}'},
            )
        resp.raise_for_status()

    latency_ms = (time.perf_counter() - start) * 1000
    data = resp.json()

    # Docling Serve retourne une liste de documents
    doc_data = data["document"] if "document" in data else data
    raw_text = doc_data.get("text", "") or _extract_text_from_elements(doc_data)

    elements = [
        DoclingElement(
            page=el.get("page_no", 1),
            bbox=el.get("bbox"),
            text=el.get("text", ""),
        )
        for el in doc_data.get("body", [])
        if el.get("text")
    ]

    tables = doc_data.get("tables", [])
    doc_type = _classify_type(raw_text)

    return ParsedDocument(
        filename=path.name,
        doc_type=doc_type,
        raw_text=raw_text,
        elements=elements,
        tables=tables,
        parse_latency_ms=latency_ms,
    )


def _extract_text_from_elements(doc_data: dict) -> str:
    parts: list[str] = []
    for el in doc_data.get("body", []):
        if text := el.get("text"):
            parts.append(text)
    return "\n".join(parts)
