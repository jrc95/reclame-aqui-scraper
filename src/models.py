"""Modelos de dados para o Reclame Aqui Scraper."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Mensagem de chat entre consumidor e empresa."""

    owner: str = Field(..., description="Autor da mensagem (consumidor ou empresa)")
    date: str = Field(..., description="Data da mensagem")
    message: str = Field(..., description="Conteúdo da mensagem")


class FinalConsideration(BaseModel):
    """Avaliação final do consumidor após resposta da empresa."""

    message: Optional[str] = Field(None, description="Comentário final do consumidor")
    service_note: Optional[str] = Field(None, description="Nota do atendimento (0-10)")
    would_do_business_again: Optional[str] = Field(
        None, description="Se faria negócio novamente"
    )
    date: Optional[str] = Field(None, description="Data da avaliação")


class Complaint(BaseModel):
    """Reclamação completa do Reclame Aqui."""

    id: str = Field(..., description="ID da reclamação")
    title: str = Field(..., description="Título da reclamação")
    description: str = Field(..., description="Descrição completa da reclamação")
    status: str = Field(..., description="Status (Resolvido, Não resolvido, etc.)")
    date: str = Field(..., description="Data da reclamação")
    location: Optional[str] = Field(None, description="Localização do consumidor")
    tags: list[str] = Field(default_factory=list, description="Tags/categorias")
    chat: list[ChatMessage] = Field(
        default_factory=list, description="Histórico de mensagens"
    )
    final_consideration: Optional[FinalConsideration] = Field(
        None, description="Avaliação final"
    )
    url: str = Field(..., description="URL da reclamação")


class CompanyInfo(BaseModel):
    """Informações básicas da empresa."""

    name: str = Field(..., description="Nome da empresa")
    slug: str = Field(..., description="Slug da empresa na URL")
    total_complaints: Optional[int] = Field(
        None, description="Total de reclamações disponíveis"
    )


class ComplaintsResponse(BaseModel):
    """Resposta da API com lista de reclamações."""

    company: CompanyInfo
    complaints: list[Complaint]
    total_returned: int = Field(..., description="Quantidade de reclamações retornadas")
    scraped_at: datetime = Field(
        default_factory=datetime.now, description="Data/hora do scraping"
    )


class ErrorResponse(BaseModel):
    """Resposta de erro da API."""

    error: str
    detail: Optional[str] = None
    status_code: int
