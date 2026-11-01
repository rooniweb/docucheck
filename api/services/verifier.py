"""Règles de vérification : complétude du dossier et cohérence entre pièces."""
from datetime import date

from api.models.schemas import (
    Anomalie,
    CandidatFields,
    DocumentExtraction,
    DocumentType,
    VerificationResult,
)

_REQUIRED_TYPES = {
    DocumentType.FORMULAIRE,
    DocumentType.IDENTITE,
    DocumentType.RELEVE,
    DocumentType.DOMICILE,
}

_NAME_FIELDS = ("nom", "prenom")


def verify(extractions: list[DocumentExtraction]) -> VerificationResult:
    anomalies: list[Anomalie] = []

    anomalies.extend(_check_completeness(extractions))
    anomalies.extend(_check_consistency(extractions))

    is_complete = not any(a.code.startswith("MISSING_") for a in anomalies)
    is_consistent = not any(a.code.startswith("MISMATCH_") for a in anomalies)

    return VerificationResult(
        anomalies=anomalies,
        is_complete=is_complete,
        is_consistent=is_consistent,
    )


def _check_completeness(extractions: list[DocumentExtraction]) -> list[Anomalie]:
    present = {e.doc_type for e in extractions}
    missing = _REQUIRED_TYPES - present
    return [
        Anomalie(
            code=f"MISSING_{t.value.upper()}",
            message=f"Pièce obligatoire absente : {t.value}",
            severity="error",
        )
        for t in missing
    ]


def _check_consistency(extractions: list[DocumentExtraction]) -> list[Anomalie]:
    anomalies: list[Anomalie] = []
    by_type = {e.doc_type: e for e in extractions}

    docs_with_identity = [
        e for e in extractions
        if e.doc_type in (DocumentType.FORMULAIRE, DocumentType.IDENTITE, DocumentType.RELEVE)
    ]

    anomalies.extend(_cross_check_names(docs_with_identity))
    anomalies.extend(_check_dates(by_type))
    anomalies.extend(_check_address(by_type))

    return anomalies


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().upper()


def _cross_check_names(docs: list[DocumentExtraction]) -> list[Anomalie]:
    """Vérifie que nom + prénom sont identiques sur toutes les pièces qui les portent."""
    anomalies: list[Anomalie] = []
    reference: DocumentExtraction | None = None

    for doc in docs:
        if not (doc.fields.nom or doc.fields.prenom):
            continue
        if reference is None:
            reference = doc
            continue

        ref_nom = _normalize(reference.fields.nom)
        ref_prenom = _normalize(reference.fields.prenom)
        cur_nom = _normalize(doc.fields.nom)
        cur_prenom = _normalize(doc.fields.prenom)

        if ref_nom and cur_nom and ref_nom != cur_nom:
            anomalies.append(Anomalie(
                code="MISMATCH_NOM",
                message=(
                    f"Nom différent entre {reference.filename} ({reference.fields.nom}) "
                    f"et {doc.filename} ({doc.fields.nom})"
                ),
                severity="error",
                piece=doc.filename,
                champ="nom",
            ))
        if ref_prenom and cur_prenom and ref_prenom != cur_prenom:
            anomalies.append(Anomalie(
                code="MISMATCH_PRENOM",
                message=(
                    f"Prénom différent entre {reference.filename} ({reference.fields.prenom}) "
                    f"et {doc.filename} ({doc.fields.prenom})"
                ),
                severity="error",
                piece=doc.filename,
                champ="prenom",
            ))

    return anomalies


def _check_dates(by_type: dict[DocumentType, DocumentExtraction]) -> list[Anomalie]:
    anomalies: list[Anomalie] = []
    today = date.today()

    formulaire = by_type.get(DocumentType.FORMULAIRE)
    identite = by_type.get(DocumentType.IDENTITE)
    releve = by_type.get(DocumentType.RELEVE)

    # Date de naissance cohérente entre formulaire et pièce d'identité
    if formulaire and identite:
        dob_f = formulaire.fields.date_naissance
        dob_i = identite.fields.date_naissance
        if dob_f and dob_i and dob_f != dob_i:
            anomalies.append(Anomalie(
                code="MISMATCH_DATE_NAISSANCE",
                message=f"Date de naissance différente : {dob_f} (formulaire) vs {dob_i} (identité)",
                severity="error",
                champ="date_naissance",
            ))

    # Année d'obtention du diplôme cohérente (pas dans le futur)
    if releve and releve.fields.annee_obtention:
        year = releve.fields.annee_obtention
        if year > today.year:
            anomalies.append(Anomalie(
                code="INVALID_ANNEE_DIPLOME",
                message=f"Année d'obtention {year} est dans le futur",
                severity="error",
                piece=releve.filename,
                champ="annee_obtention",
            ))

    return anomalies


def _check_address(by_type: dict[DocumentType, DocumentExtraction]) -> list[Anomalie]:
    anomalies: list[Anomalie] = []
    formulaire = by_type.get(DocumentType.FORMULAIRE)
    domicile = by_type.get(DocumentType.DOMICILE)

    if formulaire and domicile:
        addr_f = _normalize(formulaire.fields.adresse)
        addr_d = _normalize(domicile.fields.adresse)
        # Vérification allégée : on contrôle juste que le code postal ou la ville coïncide
        if addr_f and addr_d:
            words_f = set(addr_f.split())
            words_d = set(addr_d.split())
            overlap = words_f & words_d
            if len(overlap) < 2:
                anomalies.append(Anomalie(
                    code="MISMATCH_ADRESSE",
                    message="Adresse peu cohérente entre le formulaire et le justificatif de domicile",
                    severity="warning",
                    champ="adresse",
                ))

    return anomalies
