
# EU AI Act Assistant

Assistant conversationnel basé sur le RAG pour accompagner
les organisations dans leur compréhension du règlement européen
sur l'intelligence artificielle (EU AI Act).

## Architecture

- Frontend : Angular
- Backend métier : .NET 10
- AI Service : Python, FastAPI et LangGraph
- MCP Server : Python
- Ingestion Worker : Python
- Database : PostgreSQL
- Vector Database : Qdrant

## Prérequis

- .NET 10 SDK
- Node.js
- Python 3.12
- uv
- Docker Desktop

## Applications

| Application | Description |
|---|---|
| eu-ai-act-web | Interface Angular |
| EuAiAct.Api | API métier |
| ai-service | Orchestration IA et RAG |
| mcp-server | Outils MCP |
| ingestion-worker | Ingestion documentaire |

## Configuration

Copier `.env.example` vers `.env` et renseigner
les variables nécessaires.

## Development

Les applications peuvent être démarrées indépendamment.
Voir `docs/deployment` pour les instructions.
