from datetime import date

import pytest

from api.models.schemas import (
    CandidatFields,
    DocumentExtraction,
    DocumentType,
)


def _make_extraction(
    doc_type: DocumentType,
    filename: str,
    **field_overrides,
) -> DocumentExtraction:
    fields = CandidatFields(
        nom="Diallo",
        prenom="Mamadou",
        date_naissance=date(1998, 5, 14),
        **field_overrides,
    )
    return DocumentExtraction(
        doc_type=doc_type,
        filename=filename,
        fields=fields,
        raw_response="{}",
    )


@pytest.fixture
def complete_consistent_extractions() -> list[DocumentExtraction]:
    return [
        _make_extraction(DocumentType.FORMULAIRE, "formulaire.pdf", adresse="12 rue de la Paix, 75001 Paris", diplome="Licence"),
        _make_extraction(DocumentType.IDENTITE, "cni.pdf", nationalite="Guinéenne", numero_piece="G123456"),
        _make_extraction(DocumentType.RELEVE, "releve.pdf", diplome="Licence", etablissement="UGANC", annee_obtention=2022, moyenne=14.5),
        _make_extraction(DocumentType.DOMICILE, "quittance.pdf", adresse="12 rue de la Paix 75001 Paris"),
    ]


@pytest.fixture
def missing_identity_extractions() -> list[DocumentExtraction]:
    return [
        _make_extraction(DocumentType.FORMULAIRE, "formulaire.pdf"),
        _make_extraction(DocumentType.RELEVE, "releve.pdf"),
        _make_extraction(DocumentType.DOMICILE, "quittance.pdf"),
        # PAS de pièce d'identité
    ]


@pytest.fixture
def name_mismatch_extractions() -> list[DocumentExtraction]:
    return [
        _make_extraction(DocumentType.FORMULAIRE, "formulaire.pdf"),
        _make_extraction(DocumentType.IDENTITE, "cni.pdf", nom="Barry"),  # nom différent
        _make_extraction(DocumentType.RELEVE, "releve.pdf"),
        _make_extraction(DocumentType.DOMICILE, "quittance.pdf"),
    ]


@pytest.fixture
def dob_mismatch_extractions() -> list[DocumentExtraction]:
    return [
        _make_extraction(DocumentType.FORMULAIRE, "formulaire.pdf", date_naissance=date(1998, 5, 14)),
        _make_extraction(DocumentType.IDENTITE, "cni.pdf", date_naissance=date(1999, 3, 20)),  # date différente
        _make_extraction(DocumentType.RELEVE, "releve.pdf"),
        _make_extraction(DocumentType.DOMICILE, "quittance.pdf"),
    ]
