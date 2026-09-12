# Brand Guardian AI Compliance Auditor

Evidence-grounded video compliance auditing proof of concept. The service accepts a YouTube URL, downloads and processes the video with Azure Video Indexer, retrieves applicable compliance rules from Azure AI Search, and asks an Azure OpenAI deployment to produce a structured audit report.

This repository is currently a development proof of concept. It is **not production-ready** without the security, reliability, operational, and test work listed in [Production Readiness](#production-readiness).

## Capabilities

- FastAPI HTTP API with `/health` and `/audit` endpoints.
- YouTube video download through `yt-dlp`.
- Azure Video Indexer upload, polling, transcript extraction, and OCR extraction.
- Azure AI Search retrieval of compliance rules.
- Azure OpenAI chat completion for compliance analysis.
- Optional Azure Monitor OpenTelemetry configuration.
- PDF knowledge-base indexing script in `backend/scripts/index_documents.py`.

## Architecture

The request path is:

```text
POST /audit
	-> FastAPI router
	-> AuditController
	-> ComplianceWorkflowService
	-> LangGraph workflow
			 1. Video indexer node
			 2. Compliance auditor node
	-> AuditResponse
```

Important directories:

| Path | Responsibility |
| --- | --- |
| `backend/src/app_factory.py` | Creates the FastAPI application |
| `backend/src/router/` | HTTP routes |
| `backend/src/controllers/` | Request orchestration |
| `backend/src/services/` | Workflow service and response mapping |
| `backend/src/workflow/` | LangGraph state, nodes, and graph wiring |
| `backend/src/integrations/azure/` | Azure Video Indexer integration |
| `backend/src/config/` | Environment configuration and prompt loading |
| `backend/prompts/system/` | Versioned audit prompt files |
| `backend/data/` | PDF source material for rule indexing |
| `backend/scripts/` | Knowledge-base indexing utilities |
| `tests/` | Automated tests; currently expected to contain the project test suite |

## Requirements

- Windows, Linux, or macOS.
- Python `3.13`.
- `uv` for environment and dependency management.
- An Azure subscription with access to:
	- Azure OpenAI chat and embedding deployments.
	- Azure AI Search.
	- Azure Video Indexer.
	- Optional Application Insights.
- A credential supported by `DefaultAzureCredential` for Azure Video Indexer management calls, such as Azure CLI login, managed identity, or a service principal.
- A populated Azure AI Search index containing the compliance rules.

## Installation

Create the project environment from the repository root:

```powershell
uv sync --dev
```

Activate the environment when using commands directly:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

### Current dependency gap

The current source imports these LangChain packages:

- `langchain-openai`
- `langchain-community`
- `langchain-core`
- `langchain-text-splitters`

They are not currently declared directly in `pyproject.toml`. Add compatible pinned versions before running the API or the PDF indexing script, then regenerate the lockfile with `uv lock`.

## Environment Configuration

Create a local `.env` file in the repository root. Do not commit it. The repository `.gitignore` excludes `.env`.

```dotenv
# Application metadata
APP_NAME=Brand Guardian AI
API_TITLE=Brand Guardian AI API
API_VERSION=1.0.0
API_DESCRIPTION=API for auditing video content against brand compliance rules.

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<resource-name>.openai.azure.com/
AZURE_OPENAI_API_KEY=<optional-when-using-managed-identity>
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_CHAT_DEPLOYMENT=<chat-deployment-name>
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=<embedding-deployment-name>

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://<service-name>.search.windows.net
AZURE_SEARCH_API_KEY=<search-admin-or-query-key>
AZURE_SEARCH_INDEX_NAME=<index-name>

# Azure Video Indexer
AZURE_VI_ACCOUNT_ID=<account-id>
AZURE_VI_LOCATION=<location>
AZURE_SUBSCRIPTION_ID=<subscription-id>
AZURE_RESOURCE_GROUP=<resource-group>
AZURE_VI_NAME=<video-indexer-resource-name>

# Optional telemetry
APPLICATIONINSIGHTS_CONNECTION_STRING=<application-insights-connection-string>
```

The application loads `.env` at import time. Restart the process after changing environment values.

## Azure Setup

### 1. Azure OpenAI

Create or identify:

- A chat model deployment matching `AZURE_OPENAI_CHAT_DEPLOYMENT`.
- An embedding deployment matching `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`.
- Network and identity permissions for the runtime to invoke both deployments.

### 2. Azure AI Search

Create the search service and the index expected by the LangChain `AzureSearch` integration. The index must support the embedding model configured above. Populate it with compliance rules before calling `/audit`.

The supplied indexing script reads PDF files from `backend/data` and uploads split documents:

```powershell
uv run python backend/scripts/index_documents.py
```

The script currently requires the missing LangChain dependencies described above. Review and correct its chunking configuration before production use: the current `chunk_overlap` is larger than `chunk_size`.

### 3. Azure Video Indexer

Configure the Video Indexer resource and grant the runtime identity permission to obtain management and account access tokens. The current implementation downloads public YouTube videos, uploads them as private videos, polls until processing finishes, and extracts transcript and OCR data.

The polling implementation has no timeout or retry budget. A production deployment must add bounded polling, HTTP timeouts, retry classification, and cancellation handling.

### 4. Azure Monitor

Set `APPLICATIONINSIGHTS_CONNECTION_STRING` to enable telemetry. If it is absent, the application logs a warning and continues without Azure Monitor.

## Running the API

Start the application with the project environment:

```powershell
uv run uvicorn backend.src.app_factory:app --host 127.0.0.1 --port 8000
```

For local development with reload:

```powershell
uv run uvicorn backend.src.app_factory:app --host 127.0.0.1 --port 8000 --reload
```

The application factory is also executable directly:

```powershell
uv run python -m backend.src.app_factory
```

Do not use `--reload` in production.

## API Usage

### Health check

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected response:

```json
{
	"status": "healthy",
	"service": "Brand Guardian AI"
}
```

### Start an audit

```powershell
$body = @{ video_url = "https://www.youtube.com/watch?v=<video-id>" } | ConvertTo-Json
Invoke-RestMethod `
	-Uri http://127.0.0.1:8000/audit `
	-Method Post `
	-ContentType "application/json" `
	-Body $body
```

Equivalent `curl` request:

```bash
curl -X POST http://127.0.0.1:8000/audit \
	-H "Content-Type: application/json" \
	-d '{"video_url":"https://www.youtube.com/watch?v=<video-id>"}'
```

Response shape:

```json
{
	"session_id": "uuid",
	"video_id": "vid_uuidpre",
	"status": "PASS",
	"final_report": "Summary of findings...",
	"compliance_results": [
		{
			"category": "Claim Validation",
			"severity": "CRITICAL",
			"description": "Explanation of the violation..."
		}
	]
}
```

The audit call is synchronous and can take several minutes because it includes video download, Azure processing, polling, retrieval, and model inference.

## Testing and Quality Checks

Run the configured development checks from the repository root:

```powershell
uv run pytest -q
uv run ruff check .
uv run mypy backend
uv run pip-audit
```

The current repository does not yet provide sufficient automated tests to establish production readiness. At minimum, add tests for:

- Health and audit route behavior.
- Invalid and unsupported video URLs.
- Video Indexer success, failure, timeout, and cleanup paths.
- Empty transcript behavior.
- Azure Search and Azure OpenAI failures.
- Malformed or schema-invalid model JSON.
- Prompt loading and variable substitution.
- Service response mapping.

Use mocks or local fixtures for deterministic tests. Do not call paid Azure services from the default test suite.

## Security Notes

- Never commit `.env`, API keys, access tokens, or Application Insights connection strings.
- Use managed identity or a secret manager in deployed environments.
- The current `/audit` endpoint has no authentication, authorization, rate limiting, request-size limit, or abuse protection.
- The endpoint accepts a remote YouTube URL and causes server-side downloading. Add URL policy, domain restrictions, download limits, malware/content controls, and request timeouts before exposing it publicly.
- Avoid returning raw exception text to external clients in production.
- Review logging so URLs, model responses, and compliance data do not expose sensitive information.

## Production Readiness

This codebase is **not ready to go live** yet. The main gaps are:

1. **Dependency completeness:** LangChain packages imported by the source are missing from the current direct dependency list.
2. **Automated tests:** No test coverage currently proves API, workflow, integration-failure, or security behavior.
3. **Blocking request path:** The async FastAPI route runs synchronous download, polling, search, and model calls directly.
4. **Unbounded work:** Video polling has no deadline; requests have no explicit HTTP timeout, size limit, or cost budget.
5. **Authentication and authorization:** The API is publicly callable unless protected by an external gateway.
6. **Operational deployment:** No Dockerfile, CI workflow, deployment manifest, readiness probe, migration process, or rollback procedure is included.
7. **Observability:** Telemetry setup is optional and there are no documented metrics, alerts, correlation IDs, or audit-retention rules.
8. **Data governance:** Retention, deletion, tenant isolation, prompt-injection handling, and compliance evidence storage are not defined.
9. **Knowledge-base indexing:** The search index schema, embedding dimensions, document versioning, and re-indexing strategy are not documented or tested.
10. **Model output validation:** The response is parsed as JSON, but the business schema and allowed status/severity values are not enforced.

Treat the current repository as a local development POC until these items are addressed and validated in a staging environment.

## Development Conventions

- Use `uv` and the committed `uv.lock` for dependency resolution.
- Keep secrets in environment variables or a managed secret store.
- Keep prompt files versioned under `backend/prompts/system/`.
- Keep Azure SDK and provider calls behind integration modules where practical.
- Prefer deterministic unit tests and mocked provider boundaries.
- Run formatting, lint, type, security, and focused tests before submitting changes.
