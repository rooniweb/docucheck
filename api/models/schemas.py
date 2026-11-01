from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DocumentType(StrEnum):
    FORMULAIRE = "formulaire_inscription"
    IDENTITE = "piece_identite"
    RELEVE = "releve_notes"
    DOMICILE = "justificatif_domicile"
    INCONNU = "inconnu"


class DossierDecision(StrEnum):
    CONFORME = "conforme"
    INCOMPLET = "incomplet"
    A_VERIFIER = "a_verifier"


class DoclingElement(BaseModel):
    page: int
    bbox: list[float] | None = None
    text: str


class ParsedDocument(BaseModel):
    filename: str
    doc_type: DocumentType = DocumentType.INCONNU
    raw_text: str
    elements: list[DoclingElement] = []
    tables: list[dict[str, Any]] = []
    parse_latency_ms: float = 0.0


class CandidatFields(BaseModel):
    """Champs extraits d'un dossier d'inscription."""
    nom: str | None = None
    prenom: str | None = None
    date_naissance: date | None = None
    lieu_naissance: str | None = None
    adresse: str | None = None
    email: str | None = None
    telephone: str | None = None
    diplome: str | None = None
    etablissement: str | None = None
    annee_obtention: int | None = None
    moyenne: float | None = None
    nationalite: str | None = None
    numero_piece: str | None = None


class DocumentExtraction(BaseModel):
    doc_type: DocumentType
    filename: str
    fields: CandidatFields
    raw_response: str
    extraction_latency_ms: float = 0.0
    model_used: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0


class Anomalie(BaseModel):
    code: str
    message: str
    severity: str = Field(default="error", pattern="^(error|warning|info)$")
    piece: str | None = None
    page: int | None = None
    champ: str | None = None


class VerificationResult(BaseModel):
    anomalies: list[Anomalie] = []
    is_complete: bool = True
    is_consistent: bool = True


class DossierDecisionResult(BaseModel):
    decision: DossierDecision
    confidence: float = Field(ge=0.0, le=1.0)
    needs_human_review: bool = False
    score_details: dict[str, float] = {}


class DossierReport(BaseModel):
    dossier_id: str
    candidat_nom: str | None = None
    decision: DossierDecision
    confidence: float
    needs_human_review: bool
    anomalies: list[Anomalie]
    extractions: list[DocumentExtraction]
    verification: VerificationResult

    # Métriques
    total_latency_ms: float = 0.0
    docling_latency_ms: float = 0.0
    llm_latency_ms: float = 0.0
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    models_used: list[str] = []
    pages_processed: int = 0


class DossierSubmit(BaseModel):
    """Payload reçu par le webhook n8n."""
    dossier_id: str
    files: list[str] = Field(description="Chemins vers les fichiers PDF du dossier")
    metadata: dict[str, Any] = {}
