"""Tests unitaires du moteur de vérification (règles Python, sans LLM ni Docker)."""

from api.models.schemas import DocumentType
from api.services.verifier import verify


def test_dossier_complet_coherent_passe(complete_consistent_extractions):
    result = verify(complete_consistent_extractions)
    assert result.is_complete
    assert result.is_consistent
    assert result.anomalies == []


def test_piece_manquante_detectee(missing_identity_extractions):
    result = verify(missing_identity_extractions)
    assert not result.is_complete
    codes = [a.code for a in result.anomalies]
    assert "MISSING_PIECE_IDENTITE" in codes


def test_mismatch_nom_detecte(name_mismatch_extractions):
    result = verify(name_mismatch_extractions)
    assert not result.is_consistent
    codes = [a.code for a in result.anomalies]
    assert "MISMATCH_NOM" in codes


def test_mismatch_date_naissance_detecte(dob_mismatch_extractions):
    result = verify(dob_mismatch_extractions)
    assert not result.is_consistent
    codes = [a.code for a in result.anomalies]
    assert "MISMATCH_DATE_NAISSANCE" in codes


def test_annee_diplome_futur_detectee(complete_consistent_extractions):
    from datetime import date

    exts = list(complete_consistent_extractions)
    # Remplace le relevé par un avec une année future
    for i, e in enumerate(exts):
        if e.doc_type == DocumentType.RELEVE:
            new_fields = e.fields.model_copy(update={"annee_obtention": date.today().year + 2})
            exts[i] = e.model_copy(update={"fields": new_fields})
    result = verify(exts)
    codes = [a.code for a in result.anomalies]
    assert "INVALID_ANNEE_DIPLOME" in codes
