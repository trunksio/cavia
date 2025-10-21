# CAVIA - Deployment Guide

## System Overview

CAVIA (CV Assessment via Intelligent Agents) is an Agent Oriented Architecture system for automated CV evaluation and candidate assessment.

---

## Access Points & Credentials

### Infrastructure Services

#### PostgreSQL Database
- **Host:** `localhost`
- **Port:** `5432`
- **Database:** `cavia`
- **Username:** `cavia`
- **Password:** `caviadev123`

**Connection String:**
```
postgresql://cavia:caviadev123@localhost:5432/cavia
```

**CLI Access:**
```bash
psql -h localhost -p 5432 -U cavia -d cavia
# Password: caviadev123
```

**Docker Access:**
```bash
docker exec -it cavia-postgres psql -U cavia -d cavia
```

---

#### Redis (Task Queue)
- **Host:** `localhost`
- **Port:** `6379`
- **Password:** None (no auth required in dev)

**Connection String:**
```
redis://localhost:6379/0
```

**CLI Access:**
```bash
redis-cli -h localhost -p 6379
```

**Docker Access:**
```bash
docker exec -it cavia-redis redis-cli
```

---

#### MinIO Object Storage
- **API Endpoint:** `http://localhost:9000`
- **Console URL:** `http://localhost:9001`
- **Access Key (Username):** `minioadmin`
- **Secret Key (Password):** `minioadmin123`

**Web Console:**
- URL: http://localhost:9001
- Login with credentials above

**CLI Access (mc):**
```bash
mc alias set cavia http://localhost:9000 minioadmin minioadmin123
mc ls cavia/
```

**Buckets:**
- `cvs-raw` - Raw CV files uploaded by users
- `cvs-processed` - Processed data and parsed CVs
- `agent-artifacts` - Agent-generated artifacts

---

#### Agent Registry API
- **Base URL:** `http://localhost:8001`
- **Health Check:** `http://localhost:8001/health`
- **Documentation:** `http://localhost:8001/docs` (FastAPI Swagger UI)

**Example API Calls:**
```bash
# List all registered agents
curl http://localhost:8001/agents

# Search agents by capability
curl http://localhost:8001/agents/search?query=evaluation

# Get specific agent
curl http://localhost:8001/agents/parser-001
```

---

#### RQ Dashboard (Queue Monitoring)
- **URL:** `http://localhost:9181`
- **Auth:** None required

**Features:**
- View all RQ queues
- Monitor job status (pending, started, finished, failed)
- View worker status
- Inspect job details

---

#### Frontend Web Application
- **URL:** `http://localhost:3000`
- **Framework:** React + Vite + TailwindCSS
- **Proxy:** Nginx (proxies `/api/*` to Backend API)

**Features:**
- Drag-and-drop CV upload
- Real-time job status tracking
- Detailed evaluation results view
- Job filtering and pagination
- Responsive design

**Direct Access:**
```bash
# Open in browser
open http://localhost:3000

# Or using curl
curl http://localhost:3000
```

---

#### Backend API
- **Base URL:** `http://localhost:8000`
- **Health Check:** `http://localhost:8000/health`
- **Documentation:** `http://localhost:8000/docs` (FastAPI Swagger UI)
- **ReDoc:** `http://localhost:8000/redoc`

**Endpoints:**

**CV Upload:**
```bash
# Upload a CV for processing
curl -X POST http://localhost:8000/api/v1/cvs/upload \
  -F "file=@path/to/cv.pdf"
```

**Job Status:**
```bash
# List all jobs
curl http://localhost:8000/api/v1/jobs

# Get specific job status
curl http://localhost:8000/api/v1/jobs/{job_id}/status

# Get job result (when completed)
curl http://localhost:8000/api/v1/jobs/{job_id}/result

# Download evaluation report
curl http://localhost:8000/api/v1/jobs/{job_id}/report/download \
  -o report.md
```

**Job Filtering:**
```bash
# Filter by status
curl "http://localhost:8000/api/v1/jobs?status=completed&limit=10"
```

---

### Agentic Units

All agents register themselves on startup. View registered agents:
```bash
curl http://localhost:8001/agents | jq
```

#### Current Agents

| Agent ID | Agent Type | Queue Name | Purpose |
|----------|-----------|------------|---------|
| `parser-001` | parser | `cv-parsing` | PDF/DOCX parsing and data extraction |
| `evaluator-001` | evaluator | `cv-evaluation` | LLM-based CV evaluation (instance 1) |
| `evaluator-002` | evaluator | `cv-evaluation` | LLM-based CV evaluation (instance 2) |
| `evaluator-003` | evaluator | `cv-evaluation` | LLM-based CV evaluation (instance 3) |
| `orchestrator-001` | orchestrator | `cv-orchestration` | Workflow coordination |
| `reporter-001` | reporter | `cv-reporting` | Report generation |

---

### Ollama LLM (External Dependency)

CAVIA requires Ollama for LLM-based evaluation and reporting.

- **Default URL:** `http://host.docker.internal:11434`
- **Default Model:** `llama3:8b`
- **Alternative Models:** `mistral:7b`, `llama3:70b`

**Installation:**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull default model
ollama pull llama3:8b

# Verify
ollama list
```

**Configuration:**
Set in `.env` file:
```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3:8b
```

---

## Environment Variables

### Required Variables

Copy `.env.example` to `.env` and configure:

```env
# Database
POSTGRES_PASSWORD=caviadev123

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123

# Ollama LLM
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3:8b

# API
API_PORT=8000
API_HOST=0.0.0.0
```

---

## Docker Commands

### Start All Services
```bash
docker compose up -d
```

### Stop All Services
```bash
docker compose down
```

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f parser-agent
docker compose logs -f evaluator-agent-1
docker compose logs -f orchestrator-agent
```

### Check Service Status
```bash
docker compose ps
```

### Restart Agents
```bash
# Restart specific agent
docker compose restart parser-agent

# Restart all evaluator agents
docker compose restart evaluator-agent-1 evaluator-agent-2 evaluator-agent-3

# Rebuild and restart
docker compose up -d --build parser-agent
```

---

## Database Schema

### Key Tables

#### `agent_registry`
Stores registered agents and their capabilities.

#### `cv_jobs`
Tracks CV processing jobs through the workflow.

**Job States:**
- `pending` - Job created, not yet started
- `parsing` - CV being parsed
- `evaluating` - CV being evaluated against criteria
- `generating_report` - Report being generated
- `completed` - Job finished successfully
- `failed` - Job failed with error

#### `evaluation_criteria`
Defines evaluation criteria for CV assessment.

**Current Criteria (Sales Staff Focus):**
- `sales_experience` (weight: 0.35) - Sales track record
- `communication_skills` (weight: 0.35) - Interpersonal abilities
- `job_stability` (weight: 0.30) - Retention indicator

#### `cv_evaluations`
Stores individual evaluation results (one per criterion per CV).

**Query Examples:**
```sql
-- View all active criteria
SELECT * FROM evaluation_criteria WHERE is_active = true;

-- View all jobs
SELECT job_id, status, created_at FROM cv_jobs ORDER BY created_at DESC;

-- View evaluations for a job
SELECT * FROM cv_evaluations WHERE job_id = '<job_id>';
```

---

## Monitoring & Debugging

### Health Checks

```bash
# Agent Registry
curl http://localhost:8001/health

# PostgreSQL
docker exec cavia-postgres pg_isready -U cavia

# Redis
docker exec cavia-redis redis-cli ping

# MinIO
curl http://localhost:9000/minio/health/live
```

### View Agent Logs

```bash
# Parser Agent
docker compose logs parser-agent --tail=50

# All Evaluator Agents
docker compose logs evaluator-agent-1 evaluator-agent-2 evaluator-agent-3 --tail=50

# Orchestrator
docker compose logs orchestrator-agent --tail=50

# Reporter
docker compose logs reporter-agent --tail=50
```

### RQ Queue Inspection

```bash
# List all queues
docker exec cavia-redis redis-cli KEYS 'rq:queue:*'

# Count jobs in queue
docker exec cavia-redis redis-cli LLEN 'rq:queue:cv-parsing'
docker exec cavia-redis redis-cli LLEN 'rq:queue:cv-evaluation'
docker exec cavia-redis redis-cli LLEN 'rq:queue:cv-orchestration'
docker exec cavia-redis redis-cli LLEN 'rq:queue:cv-reporting'

# View failed jobs
docker exec cavia-redis redis-cli LRANGE 'rq:queue:failed' 0 -1
```

### Database Queries

```bash
# Connect to database
docker exec -it cavia-postgres psql -U cavia -d cavia

# View registered agents
SELECT agent_id, agent_type, name, status FROM agent_registry;

# View recent jobs
SELECT job_id, status, created_at
FROM cv_jobs
ORDER BY created_at DESC
LIMIT 10;

# View evaluation criteria
SELECT criterion_id, name, weight
FROM evaluation_criteria
WHERE is_active = true
ORDER BY weight DESC;
```

---

## Troubleshooting

### Agent Not Registering

1. Check agent logs:
   ```bash
   docker compose logs <agent-name> --tail=50
   ```

2. Verify agent-registry is healthy:
   ```bash
   curl http://localhost:8001/health
   ```

3. Check network connectivity:
   ```bash
   docker exec <agent-container> ping agent-registry
   ```

### Agent Restarting

1. Check for import errors or dependency issues in logs
2. Verify environment variables are set correctly
3. Ensure Ollama is accessible (for evaluator/reporter agents)

### Jobs Not Processing

1. Check RQ Dashboard: http://localhost:9181
2. Verify workers are running:
   ```bash
   docker compose ps
   ```
3. Check queue lengths:
   ```bash
   docker exec cavia-redis redis-cli LLEN 'rq:queue:cv-parsing'
   ```

### LLM Errors

1. Verify Ollama is running:
   ```bash
   ollama list
   curl http://localhost:11434/api/tags
   ```

2. Check model is pulled:
   ```bash
   ollama pull llama3:8b
   ```

3. Test LLM directly:
   ```bash
   curl http://localhost:11434/api/generate -d '{
     "model": "llama3:8b",
     "prompt": "Test prompt"
   }'
   ```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend (Phase 5)                   │
│                    React + Vite + TailwindCSS                │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Backend API (Phase 4)                     │
│                         FastAPI                              │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   Orchestrator Agent                         │
│              (Workflow Coordination)                         │
└──────┬──────────────────┬──────────────────┬────────────────┘
       │                  │                  │
┌──────▼───────┐  ┌───────▼────────┐  ┌─────▼──────────┐
│ Parser Agent │  │ Evaluator      │  │ Reporter Agent │
│              │  │ Agents (x3)    │  │                │
│ PDF/DOCX →   │  │ LLM Evaluation │  │ Report         │
│ ParsedCV     │  │ Score (0-100)  │  │ Generation     │
└──────┬───────┘  └───────┬────────┘  └─────┬──────────┘
       │                  │                  │
┌──────▼──────────────────▼──────────────────▼────────────────┐
│                    Infrastructure Layer                      │
│  PostgreSQL  │  Redis (RQ)  │  MinIO  │  Agent Registry    │
└──────────────────────────────────────────────────────────────┘
```

---

## Security Notes (Development)

⚠️ **WARNING:** Current configuration is for DEVELOPMENT ONLY.

**For Production:**
- Change all default passwords
- Enable SSL/TLS for all services
- Implement proper authentication/authorization
- Use secrets management (e.g., Vault)
- Enable MinIO encryption
- Configure firewall rules
- Use environment-specific `.env` files
- Enable audit logging

---

## Support & Documentation

- **Project Repository:** (Add your repo URL)
- **Issue Tracker:** (Add your issue tracker URL)
- **Documentation:** See `docs/` directory
- **API Documentation:** http://localhost:8001/docs (when API is running)
