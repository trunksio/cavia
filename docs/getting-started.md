# Getting Started with CAVIA

## Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+ (for frontend)
- 8GB+ RAM recommended
- (Optional) NVIDIA GPU with CUDA for Ollama acceleration

## Quick Start

### 1. Initial Setup

```bash
# Clone and navigate to the project
cd cavia

# Copy environment template
cp .env.example .env

# Edit .env if needed (optional for development)
nano .env

# Install shared package
make install-shared
```

### 2. Start Infrastructure

```bash
# Start core services (PostgreSQL, Redis, MinIO, Agent Registry)
make up

# Wait for services to be healthy (30-60 seconds)
# Check health status
./infrastructure/health-check.sh
```

### 3. (Optional) Start Ollama for Local LLM

```bash
# Start Ollama with default model (llama3:8b)
docker-compose -f docker-compose.yml -f docker-compose.ollama.yml up -d

# Or pull a specific model
export OLLAMA_MODEL=mistral:7b
docker-compose -f docker-compose.yml -f docker-compose.ollama.yml up -d
```

**Note:** Ollama will download ~4-8GB model on first run. This may take 10-30 minutes depending on your connection.

### 4. Verify Installation

```bash
# Check all services are running
docker-compose ps

# All services should show "Up" and "healthy"
```

Access the services:
- **MinIO Console**: http://localhost:9001 (minioadmin / minioadmin123)
- **RQ Dashboard**: http://localhost:9181 (monitor job queues)
- **Agent Registry API**: http://localhost:8001/docs (OpenAPI docs)
- **PostgreSQL**: localhost:5432 (cavia / caviadev123)

### 5. Test the Agent Template

```bash
# Build the template agent
cd agents/template
docker build -t cavia-agent-template .

# Run the template agent
docker run -it --rm \
  --network cavia-network \
  -e DATABASE_URL=postgresql://cavia:caviadev123@cavia-postgres:5432/cavia \
  -e REDIS_URL=redis://cavia-redis:6379/0 \
  -e AGENT_ID=test-agent-001 \
  cavia-agent-template

# In another terminal, check if agent registered
curl http://localhost:8001/agents | jq
```

## Project Structure

```
cavia/
├── agents/                    # Agentic Units
│   ├── template/             # Template agent (example)
│   ├── parser/               # CV parser agent (Phase 3)
│   ├── evaluator/            # Evaluation agents (Phase 3)
│   ├── orchestrator/         # Orchestrator agent (Phase 3)
│   └── reporter/             # Report generator (Phase 3)
├── backend/
│   └── registry/             # Agent registry service ✅
├── frontend/                 # React UI (Phase 5)
├── shared/
│   └── python/
│       └── cavia_common/     # Shared utilities ✅
├── infrastructure/           # Infrastructure configs ✅
├── docker-compose.yml        # Core services ✅
└── docker-compose.ollama.yml # Optional Ollama ✅
```

## Next Steps

Now that the infrastructure is ready, you can:

1. **Build CV Processing Agents** (Phase 3)
   - Parser Agent: Extract structured data from CVs
   - Evaluator Agents: Evaluate against criteria
   - Orchestrator: Coordinate the swarm
   - Reporter: Generate evaluation reports

2. **Build Backend API** (Phase 4)
   - FastAPI service for CV upload
   - Criteria management
   - Results retrieval

3. **Build Frontend** (Phase 5)
   - React UI for CV submission
   - Dashboard for results
   - Criteria configuration

## Development Workflow

```bash
# Start all services
make up

# View logs
make logs

# Stop services
make down

# Clean everything (including data)
make clean

# Run tests
make test
```

## Troubleshooting

### Services won't start

```bash
# Check logs
docker-compose logs

# Restart specific service
docker-compose restart postgres

# Full restart
make down && make up
```

### Database connection errors

```bash
# Check PostgreSQL is ready
docker-compose exec postgres pg_isready -U cavia

# Reinitialize database
make init-db
```

### Ollama out of memory

- Reduce model size: Use `llama3:8b` instead of larger models
- Increase Docker memory limit in Docker Desktop settings
- Use CPU-only mode (slower but works with less RAM)

### Agent won't register

- Check agent registry is running: `curl http://localhost:8001/health`
- Check network connectivity: `docker network ls | grep cavia`
- Check agent logs: `docker logs <agent-container-id>`

## Monitoring

### RQ Dashboard
Visit http://localhost:9181 to see:
- Active queues
- Job status
- Failed jobs
- Worker status

### MinIO Console
Visit http://localhost:9001 to see:
- Uploaded CVs
- Processed results
- Storage usage

### Agent Registry
Visit http://localhost:8001/docs to:
- View registered agents
- Test API endpoints
- See agent capabilities

## Configuration

Key environment variables in `.env`:

```bash
# Database
POSTGRES_PASSWORD=caviadev123

# MinIO credentials
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123

# Ollama model
OLLAMA_MODEL=llama3:8b

# Agent settings
AGENT_TIMEOUT=60
AGENT_HEARTBEAT_INTERVAL=30

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## Production Deployment

For production deployment, see [docs/deployment.md](./deployment.md) (coming in Phase 7).

Key considerations:
- Use strong passwords (change SECRET_KEY, POSTGRES_PASSWORD, MINIO credentials)
- Enable TLS/SSL
- Use external PostgreSQL (not Docker container)
- Set up proper monitoring and alerting
- Configure backup strategies
- Use Kubernetes for orchestration (optional)
