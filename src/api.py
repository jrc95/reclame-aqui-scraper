"""FastAPI endpoints para o Reclame Aqui Scraper."""

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .models import CompanyInfo, ComplaintsResponse, ErrorResponse
from .scraper import get_complaints, search_company

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Cria app FastAPI
app = FastAPI(
    title="Reclame Aqui Scraper API",
    description="API para extrair reclamações do Reclame Aqui",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique os domínios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Reclame Aqui Scraper API"}


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check detalhado."""
    return {
        "status": "healthy",
        "version": "0.1.0",
    }


@app.get(
    "/api/complaints/{company_slug}",
    response_model=ComplaintsResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    tags=["Complaints"],
)
async def get_company_complaints(
    company_slug: str,
    limit: int = Query(default=10, ge=1, le=100, description="Número de reclamações"),
    status: Optional[str] = Query(
        default=None,
        description="Filtro de status: EVALUATED, NOT_SOLVED, SOLVED",
    ),
):
    """
    Obtém as últimas reclamações de uma empresa.

    - **company_slug**: Identificador da empresa na URL do Reclame Aqui
      (ex: "itau", "magazine-luiza-loja-online", "nubank")
    - **limit**: Número máximo de reclamações a retornar (1-100)
    - **status**: Filtro opcional por status da reclamação

    Exemplos de company_slug:
    - Itaú: `itau`
    - Magazine Luiza: `magazine-luiza-loja-online`
    - Nubank: `nubank`
    - Spotify: `spotify`
    """
    try:
        # Monta filtro de status
        status_filter = ""
        if status:
            status_filter = f"&status={status.upper()}"

        # Faz scraping
        result = get_complaints(
            company_slug=company_slug,
            limit=limit,
            status_filter=status_filter,
        )

        if not result.complaints:
            raise HTTPException(
                status_code=404,
                detail=f"Nenhuma reclamação encontrada para '{company_slug}'",
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar requisição: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno: {str(e)}",
        )


@app.get(
    "/api/search",
    response_model=list[CompanyInfo],
    tags=["Search"],
)
async def search_companies(
    q: str = Query(..., min_length=2, description="Termo de busca"),
):
    """
    Busca empresas pelo nome.

    - **q**: Termo de busca (mínimo 2 caracteres)

    Retorna lista de empresas com nome e slug.
    """
    try:
        companies = search_company(q)

        if not companies:
            raise HTTPException(
                status_code=404,
                detail=f"Nenhuma empresa encontrada para '{q}'",
            )

        return companies

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na busca: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno: {str(e)}",
        )


# Entry point para rodar com uvicorn
if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))

    uvicorn.run("src.api:app", host=host, port=port, reload=True)
