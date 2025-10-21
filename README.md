# CAVIA - CV Agent-based Intelligent Assessment

A CV processing system built using **Agent Oriented Architecture (AOA)** for intelligent, scalable, and explainable candidate evaluation.

## Overview

CAVIA uses a swarm of specialized Agentic Units to process and evaluate CVs against configurable criteria. Each agent is a self-contained Docker container with its own LLM, communicating via Redis RQ and coordinated by a central orchestrator.

## Architecture

```
┌─────────────┐
│   React UI  │
└──────┬──────┘
       │
┌──────▼──────────┐
│  FastAPI Backend│
└──────┬──────────┘
       │
┌──────▼──────────┐         ┌──────────────┐
│  Orchestrator   │◄────────┤ Agent Registry│
│     Agent       │         └──────────────┘
└──────┬──────────┘
       │
       ├──► Parser Agent
       ├──► Evaluator Agent 1
       ├──► Evaluator Agent 2
       ├──► Evaluator Agent 3
       └──► Reporter Agent
```

## Tech Stack

- **Frontend**: React + Vite + TailwindCSS
- **Backend**: FastAPI (Python 3.11+)
- **Agents**: Docker containers + Ollama (LLaMA 3 / Mistral)
- **Queue**: Redis + RQ
- **Storage**: MinIO (S3-compatible)
- **Database**: PostgreSQL + pgvector
- **Orchestration**: Docker Compose

## Quick Start

```bash
# Start infrastructure
docker-compose up -d

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install

# Start development servers
npm run dev  # Frontend (port 5173)
python -m uvicorn main:app --reload  # Backend (port 8000)
```

## Project Structure

```
cavia/
├── agents/                 # Agentic Units
│   ├── parser/            # CV parsing agent
│   ├── evaluator/         # Criteria evaluation agent
│   ├── orchestrator/      # Swarm coordination agent
│   └── reporter/          # Report generation agent
├── backend/               # FastAPI application
├── frontend/              # React application
├── shared/                # Shared libraries
│   └── python/
│       └── cavia_common/  # Common utilities package
├── infrastructure/        # Infrastructure configs
├── tests/                 # Test suite
├── docs/                  # Documentation
└── docker-compose.yml     # Development environment
```

## Development Phases

- ✅ **Phase 1**: Infrastructure Foundation (Complete)
- ✅ **Phase 2**: Base Agentic Unit Template (Complete)
- ⏳ **Phase 3**: CV Processing Agent Swarm
- ⏳ **Phase 4**: Backend API Development
- ⏳ **Phase 5**: React Frontend
- ⏳ **Phase 6**: Integration & Orchestration
- ⏳ **Phase 7**: Observability & Iteration

**Overall Progress:** 28% (2/7 phases complete)

## Key Features

- **Configurable Criteria**: Define custom evaluation criteria via UI
- **Swarm Intelligence**: Multiple specialized agents collaborate on decisions
- **Semantic Registry**: Agents self-register and discover each other
- **Explainable Results**: Clear reasoning for accept/reject decisions
- **Scalable**: Process hundreds of CVs concurrently
- **AOA Principles**: Self-contained, discoverable, memory-enabled agents

## Documentation

- [AOA Architecture](./AOA.md)
- [Agent Development Guide](./docs/agent-development.md) (Coming soon)
- [API Documentation](./docs/api.md) (Coming soon)
- [Deployment Guide](./docs/deployment.md) (Coming soon)

## License

MIT
