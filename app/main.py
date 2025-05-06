from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.routers import exam

# Configuração básica de logging
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="API Elaborador de Provas",
    description="API para servir e corrigir provas de múltipla escolha.",
    version="0.1.0"
)

# Configuração do CORS (ajuste conforme necessário para produção)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permite todas as origens (cuidado em produção!)
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(exam.router, prefix="/api", tags=["Exams"])

@app.get("/health", tags=["Health Check"])
def health_check():
    return {"status": "ok"}
