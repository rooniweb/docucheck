from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
import shutil
import uuid
from pathlib import Path

from api.models.schemas import DossierReport, DossierSubmit
from api.services.pipeline import process_dossier

router = APIRouter(prefix="/dossiers", tags=["dossiers"])

_UPLOAD_DIR = Path("/app/data/uploads")
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/submit", response_model=DossierReport)
async def submit_dossier(payload: DossierSubmit):
    """Traite un dossier dont les fichiers sont déjà accessibles sur le système de fichiers."""
    try:
        report = await process_dossier(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return report


@router.post("/upload", response_model=DossierReport)
async def upload_dossier(
    files: list[UploadFile] = File(...),
    dossier_id: str = Form(default=None),
):
    """Reçoit les fichiers PDF par multipart/form-data, les sauvegarde, puis traite le dossier."""
    dossier_id = dossier_id or str(uuid.uuid4())
    dossier_dir = _UPLOAD_DIR / dossier_id
    dossier_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[str] = []
    for upload in files:
        dest = dossier_dir / (upload.filename or f"{uuid.uuid4()}.pdf")
        with dest.open("wb") as f:
            shutil.copyfileobj(upload.file, f)
        saved_paths.append(str(dest))

    payload = DossierSubmit(dossier_id=dossier_id, files=saved_paths)
    try:
        report = await process_dossier(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return report


@router.get("/health")
async def health():
    return {"status": "ok"}
