# Reclame Aqui Scraper API

API para extrair reclamações do [Reclame Aqui](https://www.reclameaqui.com.br).

## Features

- Buscar empresa pelo nome
- Extrair últimas reclamações de uma empresa
- Filtrar por status (resolvido, não resolvido, avaliado)
- API RESTful com FastAPI
- Documentação automática (Swagger/OpenAPI)

## Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/reclame-aqui-scraper.git
cd reclame-aqui-scraper
```

### 2. Crie um ambiente virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

```bash
cp .env.example .env
# Edite o arquivo .env conforme necessário
```

## Uso

### Rodar a API localmente

```bash
# Opção 1: Via uvicorn
uvicorn src.api:app --reload

# Opção 2: Via Python
python -m src.api
```

A API estará disponível em `http://localhost:8000`.

### Documentação

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Endpoints

### GET /api/complaints/{company_slug}

Obtém as últimas reclamações de uma empresa.

**Parâmetros:**
- `company_slug` (path): Identificador da empresa na URL do Reclame Aqui
- `limit` (query, opcional): Número de reclamações (1-100, default: 10)
- `status` (query, opcional): Filtro de status (EVALUATED, NOT_SOLVED, SOLVED)

**Exemplo:**
```bash
curl "http://localhost:8000/api/complaints/nubank?limit=5"
```

**Resposta:**
```json
{
  "company": {
    "name": "Nubank",
    "slug": "nubank",
    "total_complaints": 500
  },
  "complaints": [
    {
      "id": "123456",
      "title": "Cobrança indevida",
      "description": "Fui cobrado indevidamente...",
      "status": "Resolvido",
      "date": "05/02/2026 às 10:30",
      "location": "São Paulo - SP",
      "tags": ["cobrança", "cartão de crédito"],
      "chat": [...],
      "final_consideration": {...},
      "url": "https://www.reclameaqui.com.br/..."
    }
  ],
  "total_returned": 5,
  "scraped_at": "2026-02-05T15:30:00"
}
```

### GET /api/search

Busca empresas pelo nome.

**Parâmetros:**
- `q` (query): Termo de busca (mínimo 2 caracteres)

**Exemplo:**
```bash
curl "http://localhost:8000/api/search?q=magazine"
```

**Resposta:**
```json
[
  {
    "name": "Magazine Luiza",
    "slug": "magazine-luiza-loja-online"
  },
  {
    "name": "Magazine Luiza Loja Física",
    "slug": "magazine-luiza-loja-fisica"
  }
]
```

## Estrutura do Projeto

```
reclame-aqui-scraper/
├── src/
│   ├── __init__.py
│   ├── api.py          # Endpoints FastAPI
│   ├── models.py       # Modelos Pydantic
│   └── scraper.py      # Core do scraping
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

## Limitações

- O Reclame Aqui limita a visualização a **50 páginas** (~500 reclamações por consulta)
- Requisições excessivas podem resultar em bloqueio temporário
- A estrutura HTML do site pode mudar, quebrando os seletores

## Deploy

### Railway

1. Crie uma conta no [Railway](https://railway.app)
2. Conecte seu repositório GitHub
3. Configure as variáveis de ambiente
4. Deploy automático a cada push

### Render

1. Crie uma conta no [Render](https://render.com)
2. New Web Service → Connect repo
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn src.api:app --host 0.0.0.0 --port $PORT`

## Licença

MIT
