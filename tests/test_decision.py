"""Tests du moteur de décision TypeSafe Jev (confiance + routage)."""
import pytest

from api.models.schemas import DossierDecision
from api.services.decision import decide
from api.services.verifier import verify


def test_decision_conforme(complete_consistent_extractions):
    verification = verify(complete_consistent_extractions)
    result = decide(verification)
    assert result.decision == DossierDecision.CONFORME
    assert result.confidence >= 0.80
    assert not result.needs_human_review


def test_decision_incomplet(missing_identity_extractions):
    verification = verify(missing_identity_extractions)
    result = decide(verification)
    assert result.decision == DossierDecision.INCOMPLET
    assert result.needs_human_review


def test_decision_a_verifier(name_mismatch_extractions):
    verification = verify(name_mismatch_extractions)
    result = decide(verification)
    assert result.decision in (DossierDecision.A_VERIFIER, DossierDecision.INCOMPLET)
    assert result.confidence < 1.0


def test_confiance_sous_seuil_envoie_en_revue_humaine(dob_mismatch_extractions):
    verification = verify(dob_mismatch_extractions)
    result = decide(verification)
    # Un mismatch date doit faire descendre la confiance sous 0.80
    assert result.needs_human_review or result.confidence < 1.0
