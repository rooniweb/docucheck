"""Moteur de décision TypeSafe Jev : classifie le dossier avec un score de confiance.

TypeSafe Jev est un moteur de règles typées qui produit une décision + score à partir
de signaux booléens pondérés. Même logique que pour le tri d'e-mails, appliquée ici
au contrôle de dossiers.
"""
from api.models.schemas import (
    Anomalie,
    DossierDecision,
    DossierDecisionResult,
    VerificationResult,
)
from api.core.config import settings


_WEIGHTS: dict[str, float] = {
    "complete": 0.40,
    "consistent": 0.35,
    "no_errors": 0.15,
    "no_warnings": 0.10,
}


def decide(verification: VerificationResult) -> DossierDecisionResult:
    """Produit une décision binaire + score de confiance [0, 1]."""
    errors = [a for a in verification.anomalies if a.severity == "error"]
    warnings = [a for a in verification.anomalies if a.severity == "warning"]

    signals: dict[str, bool] = {
        "complete": verification.is_complete,
        "consistent": verification.is_consistent,
        "no_errors": len(errors) == 0,
        "no_warnings": len(warnings) == 0,
    }

    score = sum(_WEIGHTS[k] for k, v in signals.items() if v)
    score = round(score, 4)

    if score >= settings.confidence_threshold and not errors:
        decision = DossierDecision.CONFORME
    elif not verification.is_complete:
        decision = DossierDecision.INCOMPLET
    else:
        decision = DossierDecision.A_VERIFIER

    needs_human = score < settings.confidence_threshold

    return DossierDecisionResult(
        decision=decision,
        confidence=score,
        needs_human_review=needs_human,
        score_details={k: float(v) for k, v in signals.items()},
    )
