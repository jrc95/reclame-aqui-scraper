"""Core do scraper para o Reclame Aqui usando Firecrawl."""

import logging
import os
import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from firecrawl import Firecrawl

from .models import (
    ChatMessage,
    Complaint,
    CompanyInfo,
    ComplaintsResponse,
    FinalConsideration,
)

# Carrega variáveis de ambiente
load_dotenv()

logger = logging.getLogger(__name__)

# Inicializa o cliente Firecrawl
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
if not FIRECRAWL_API_KEY:
    raise ValueError("FIRECRAWL_API_KEY não configurada. Verifique o arquivo .env")

firecrawl = Firecrawl(api_key=FIRECRAWL_API_KEY)

BASE_URL = "https://www.reclameaqui.com.br"


class ScraperError(Exception):
    """Erro durante o scraping."""
    pass


def _scrape_url(url: str) -> str:
    """Faz scraping de uma URL usando Firecrawl e retorna o HTML."""
    try:
        logger.info(f"Firecrawl scraping: {url}")
        result = firecrawl.scrape(url, formats=["html"])
        
        if result and hasattr(result, 'html'):
            return result.html
        elif isinstance(result, dict) and 'html' in result:
            return result['html']
        else:
            logger.warning(f"Resultado inesperado do Firecrawl: {type(result)}")
            return ""
    except Exception as e:
        logger.error(f"Erro no Firecrawl: {e}")
        raise ScraperError(f"Erro ao fazer scraping de {url}: {e}")


def _scrape_url_markdown(url: str) -> str:
    """Faz scraping de uma URL usando Firecrawl e retorna markdown."""
    try:
        logger.info(f"Firecrawl scraping (markdown): {url}")
        result = firecrawl.scrape(url, formats=["markdown"])
        
        if result and hasattr(result, 'markdown'):
            return result.markdown
        elif isinstance(result, dict) and 'markdown' in result:
            return result['markdown']
        else:
            logger.warning(f"Resultado inesperado do Firecrawl: {type(result)}")
            return ""
    except Exception as e:
        logger.error(f"Erro no Firecrawl: {e}")
        raise ScraperError(f"Erro ao fazer scraping de {url}: {e}")


def get_complaint_urls_from_markdown(markdown: str, company_slug: str, limit: int = 10) -> list[str]:
    """Extrai URLs de reclamações do markdown da página de lista."""
    urls: list[str] = []
    
    # Regex para encontrar links de reclamações no markdown
    # Formato: [título](https://www.reclameaqui.com.br/empresa/titulo-reclamacao_ID/)
    pattern = rf'\[([^\]]+)\]\((https://www\.reclameaqui\.com\.br/{company_slug}/[^)]+)\)'
    matches = re.findall(pattern, markdown)
    
    logger.info(f"Regex encontrou {len(matches)} matches para {company_slug}")
    
    for title, url in matches:
        # Filtra URLs que parecem ser reclamações (têm underscore seguido de ID)
        if "_" in url and url not in urls:
            urls.append(url)
            logger.info(f"URL encontrada: {url[:80]}...")
            if len(urls) >= limit:
                break
    
    return urls


def get_total_pages(company_slug: str) -> int:
    """Retorna o total de páginas de reclamações disponíveis."""
    try:
        url = f"{BASE_URL}/empresa/{company_slug}/lista-reclamacoes/"
        markdown = _scrape_url_markdown(url)
        
        # Procura por "Página X de Y" ou similar
        match = re.search(r'(\d+)\s+de\s+(\d+)', markdown)
        if match:
            total = int(match.group(2))
            return min(total, 50)  # Máximo 50 páginas
        
        return 1
    except Exception as e:
        logger.error(f"Erro ao obter total de páginas: {e}")
        return 1


def get_complaint_urls(
    company_slug: str, limit: int = 10, status_filter: str = ""
) -> list[str]:
    """Coleta URLs das reclamações da lista usando Firecrawl."""
    urls: list[str] = []
    page = 1
    
    while len(urls) < limit:
        list_url = f"{BASE_URL}/empresa/{company_slug}/lista-reclamacoes/?pagina={page}{status_filter}"
        
        try:
            markdown = _scrape_url_markdown(list_url)
            page_urls = get_complaint_urls_from_markdown(markdown, company_slug, limit - len(urls))
            
            if not page_urls:
                logger.warning(f"Nenhuma URL encontrada na página {page}")
                break
            
            urls.extend(page_urls)
            logger.info(f"Página {page}: encontradas {len(page_urls)} URLs")
            
            page += 1
            
            # Limite de páginas para evitar loop infinito
            if page > 10:
                break
                
        except ScraperError as e:
            logger.error(f"Erro ao coletar URLs da página {page}: {e}")
            break

    return urls[:limit]


def _parse_chat_from_html(soup: BeautifulSoup) -> list[ChatMessage]:
    """Extrai histórico de chat da reclamação."""
    chat_messages: list[ChatMessage] = []

    interaction_list = soup.find("div", {"data-testid": "complaint-interaction-list"})
    if not interaction_list:
        return chat_messages

    for container in interaction_list.find_all(
        "div", {"data-testid": "complaint-interaction"}
    ):
        try:
            owner_elem = container.find("h2")
            date_elem = container.find("span", class_=re.compile(r"sc-"))
            message_elem = container.find("p")

            if owner_elem and message_elem:
                if not container.find("h2", {"type": "FINAL_ANSWER"}):
                    chat_messages.append(
                        ChatMessage(
                            owner=owner_elem.text.strip(),
                            date=date_elem.text.strip() if date_elem else "",
                            message=message_elem.text.strip(),
                        )
                    )
        except Exception as e:
            logger.warning(f"Erro ao parsear mensagem de chat: {e}")

    return chat_messages


def _parse_final_consideration_from_html(soup: BeautifulSoup) -> Optional[FinalConsideration]:
    """Extrai avaliação final do consumidor."""
    evaluation = soup.find("div", {"data-testid": "complaint-evaluation-interaction"})

    if not evaluation:
        return None

    try:
        message_elem = evaluation.find("div", {"data-testid": "complaint-interaction"})
        date_elem = evaluation.find("span")
        business_elem = evaluation.find("div", {"data-testid": "complaint-deal-again"})

        service_note = None
        note_matches = re.findall(r"\d+", evaluation.text)
        if note_matches:
            service_note = note_matches[-1]

        return FinalConsideration(
            message=message_elem.find("p").text.strip()
            if message_elem and message_elem.find("p")
            else None,
            service_note=service_note,
            would_do_business_again=business_elem.text.strip()
            if business_elem
            else None,
            date=date_elem.text.strip() if date_elem else None,
        )
    except Exception as e:
        logger.warning(f"Erro ao parsear avaliação final: {e}")
        return None


def _parse_tags_from_html(soup: BeautifulSoup) -> list[str]:
    """Extrai tags/categorias da reclamação."""
    tags: list[str] = []

    tag_list = soup.find("ul", class_=re.compile(r"sc-"))
    if tag_list:
        for tag in tag_list.find_all("li"):
            tags.append(tag.text.strip())

    return tags


def scrape_complaint(url: str) -> Optional[Complaint]:
    """Extrai dados de uma reclamação específica usando Firecrawl (markdown)."""
    try:
        markdown = _scrape_url_markdown(url)
        if not markdown:
            logger.warning(f"Markdown vazio para: {url}")
            return None
        
        # Extrai título (primeira linha com #)
        title_match = re.search(r'^#\s+(.+)$', markdown, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else "Sem título"
        
        # Extrai ID
        id_match = re.search(r'\*\*ID:\*\*\s*(\d+)', markdown)
        complaint_id = id_match.group(1) if id_match else ""
        
        # Se não encontrou no markdown, tenta extrair da URL
        if not complaint_id:
            url_id_match = re.search(r'_([a-zA-Z0-9]+)/?$', url)
            if url_id_match:
                complaint_id = url_id_match.group(1)
        
        # Extrai status (aparece após imagem com "Reclamação")
        status = "Desconhecido"
        # Procura por padrões como "Não respondida", "Respondida", "Resolvido"
        status_patterns = [
            r'!\[Reclamação[^\]]*\]\([^)]+\)\s*\n+([^\n\[]+)',
            r'Status da reclamação:\s*\n+[^\n]*\n+([^\n]+)',
        ]
        for pattern in status_patterns:
            status_match = re.search(pattern, markdown)
            if status_match:
                potential_status = status_match.group(1).strip()
                if potential_status and len(potential_status) < 50:
                    status = potential_status
                    break
        
        # Extrai data e local
        # Formato: "João Pessoa - PB\n\n05/02/2026 às 20:34"
        location = None
        date = ""
        
        # Procura pela seção que contém local e data
        loc_date_match = re.search(
            r'\[Reclamar dessa empresa\][^\n]*\n+([^\n]+)\n+(\d{2}/\d{2}/\d{4}[^\n]*)',
            markdown
        )
        if loc_date_match:
            location = loc_date_match.group(1).strip()
            date = loc_date_match.group(2).strip()
        else:
            # Tenta só a data
            date_match = re.search(r'(\d{2}/\d{2}/\d{4}\s+às\s+\d{2}:\d{2})', markdown)
            if date_match:
                date = date_match.group(1)
        
        # Extrai descrição (texto principal após o ID)
        description = ""
        # A descrição geralmente vem após "**ID:** XXXXX" e antes de "Deixe sua reação"
        desc_match = re.search(
            r'\*\*ID:\*\*\s*\d+\s*\n+(?:Status da reclamação:[^\n]*\n+[^\n]*\n+)?([^\n]+(?:\n+[^\n]+)*?)(?:\n+Deixe sua rea|\n+Compartilhe|\n+\[RA Ads\])',
            markdown
        )
        if desc_match:
            description = desc_match.group(1).strip()
            # Remove linhas que são imagens ou links
            description = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', description)
            description = re.sub(r'\n+', ' ', description).strip()
        
        if not title or title == "Sem título":
            logger.warning(f"Título não encontrado: {url}")
            return None
        
        return Complaint(
            id=complaint_id,
            title=title,
            description=description,
            status=status,
            date=date,
            location=location,
            tags=[],  # Tags requerem parsing mais complexo
            chat=[],  # Chat requer parsing adicional
            final_consideration=None,  # Avaliação final requer parsing adicional
            url=url,
        )

    except ScraperError as e:
        logger.error(f"Erro ao fazer scraping de {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao processar {url}: {e}")
        return None


def get_complaints(
    company_slug: str,
    limit: int = 10,
    status_filter: str = "",
) -> ComplaintsResponse:
    """
    Obtém as últimas reclamações de uma empresa usando Firecrawl.

    Args:
        company_slug: Slug da empresa (ex: "nubank", "magazine-luiza-loja-online")
        limit: Número máximo de reclamações a retornar
        status_filter: Filtro de status opcional (ex: "&status=SOLVED")

    Returns:
        ComplaintsResponse com as reclamações encontradas
    """
    logger.info(f"Iniciando scraping para {company_slug}, limite: {limit}, status: {status_filter or 'todos'}")

    # Coleta URLs das reclamações
    urls = get_complaint_urls(company_slug, limit, status_filter)
    logger.info(f"Encontradas {len(urls)} URLs de reclamações")

    # Faz scraping de cada reclamação
    complaints: list[Complaint] = []
    for i, url in enumerate(urls):
        logger.info(f"Processando {i + 1}/{len(urls)}: {url}")
        complaint = scrape_complaint(url)
        if complaint:
            complaints.append(complaint)

    # Monta resposta
    total_pages = get_total_pages(company_slug)

    return ComplaintsResponse(
        company=CompanyInfo(
            name=company_slug.replace("-", " ").title(),
            slug=company_slug,
            total_complaints=total_pages * 10,
        ),
        complaints=complaints,
        total_returned=len(complaints),
    )


def search_company(query: str) -> list[CompanyInfo]:
    """
    Busca empresas pelo nome usando Firecrawl.

    Args:
        query: Termo de busca

    Returns:
        Lista de empresas encontradas
    """
    search_url = f"{BASE_URL}/busca/?q={query}"

    try:
        # Usa wait para aguardar o carregamento dinâmico do JavaScript
        logger.info(f"Buscando empresas: {query}")
        result = firecrawl.scrape(
            search_url,
            formats=["markdown"],
            actions=[
                {"type": "wait", "milliseconds": 3000}
            ]
        )
        
        markdown = ""
        if result and hasattr(result, 'markdown'):
            markdown = result.markdown
        elif isinstance(result, dict) and 'markdown' in result:
            markdown = result['markdown']
        
        if not markdown:
            logger.warning("Nenhum markdown retornado na busca")
            return []
        
        # Procura links de empresas no markdown
        # Formato: [Nome](https://www.reclameaqui.com.br/empresa/slug/)
        pattern = r'\[([^\]]+)\]\((https://www\.reclameaqui\.com\.br/empresa/([^/\)]+)/?)\)'
        matches = re.findall(pattern, markdown)
        
        logger.info(f"Encontrados {len(matches)} matches de empresas")

        # Usa dicionário para guardar o melhor nome para cada slug
        slug_to_name: dict[str, str] = {}
        
        for name, url, slug in matches:
            # Filtra slugs inválidos
            if ("lista-reclamacoes" in slug 
                or len(slug) <= 1
                or slug.startswith("ra-")):
                continue
            
            # Limpa o nome
            clean_name = name.strip()
            
            # Ignora nomes inválidos (muito curtos ou com markdown)
            if (not clean_name 
                or len(clean_name) <= 2 
                or "**" in clean_name
                or "\\" in clean_name
                or "%" in clean_name):
                continue
            
            # Guarda o nome mais longo para cada slug
            if slug not in slug_to_name or len(clean_name) > len(slug_to_name[slug]):
                slug_to_name[slug] = clean_name
        
        # Converte para lista de CompanyInfo
        companies: list[CompanyInfo] = []
        for slug, name in slug_to_name.items():
            companies.append(CompanyInfo(name=name, slug=slug))
            logger.info(f"Empresa encontrada: {name} ({slug})")

        return companies[:10]

    except Exception as e:
        logger.error(f"Erro na busca: {e}")
        return []
