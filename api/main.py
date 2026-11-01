from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import dossiers

app = FastAPI(
    title="DocuCheck API",
    description="Contrôle automatisé de dossiers d'inscription — parsing Docling + extraction LLM + vérification TypeSafe Jev",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dossiers.router)


@app.get("/")
async def root():
    return {
        "service": "DocuCheck API",
        "docs": "/docs",
        "health": "/dossiers/health",
    }
