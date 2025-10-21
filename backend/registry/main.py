"""
Agent Registry Service - Central discovery and registration for Agentic Units
"""

import sys
from contextlib import asynccontextmanager
from typing import List, Optional

sys.path.insert(0, "/shared")

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

from cavia_common import (
    get_settings,
    setup_logging,
    get_logger,
    get_db_manager,
    AgentRegistration,
    AgentStatus,
)

# Setup
setup_logging()
logger = get_logger(__name__)
settings = get_settings()


# Pydantic models for API
class AgentRegisterRequest(BaseModel):
    agent_id: str
    agent_type: str
    name: str
    description: str
    capabilities: dict
    queue_name: str


class AgentSearchRequest(BaseModel):
    query: str
    limit: int = 10


class AgentInfo(BaseModel):
    agent_id: str
    agent_type: str
    name: str
    description: str
    capabilities: dict
    queue_name: str
    status: str


# Global embedding model
embedding_model: Optional[SentenceTransformer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    global embedding_model

    # Startup
    logger.info("Starting Agent Registry Service")

    # Load embedding model
    logger.info("Loading embedding model", model=settings.embedding_model)
    embedding_model = SentenceTransformer(settings.embedding_model)

    # Initialize database
    db = get_db_manager()
    logger.info("Database connection established")

    yield

    # Shutdown
    logger.info("Shutting down Agent Registry Service")


# Create FastAPI app
app = FastAPI(
    title="CAVIA Agent Registry",
    description="Central registry and discovery service for Agentic Units",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "agent-registry",
        "version": "0.1.0",
    }


@app.post("/agents/register", status_code=201)
async def register_agent(request: AgentRegisterRequest):
    """Register a new agent or update existing registration"""
    try:
        db = get_db_manager()

        # Generate semantic embedding
        description = f"{request.name}: {request.description}"
        embedding = embedding_model.encode(description)

        # Register in database
        success = db.register_agent(
            agent_id=request.agent_id,
            agent_type=request.agent_type,
            name=request.name,
            description=request.description,
            capabilities=request.capabilities,
            queue_name=request.queue_name,
            semantic_embedding=embedding,
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to register agent")

        logger.info("Agent registered", agent_id=request.agent_id)

        return {
            "status": "success",
            "agent_id": request.agent_id,
            "message": "Agent registered successfully",
        }

    except Exception as e:
        logger.error("Registration error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/heartbeat")
async def agent_heartbeat(agent_id: str):
    """Update agent heartbeat"""
    try:
        db = get_db_manager()
        success = db.update_heartbeat(agent_id)

        if not success:
            raise HTTPException(status_code=404, detail="Agent not found")

        return {"status": "success", "agent_id": agent_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Heartbeat error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents", response_model=List[AgentInfo])
async def list_agents(
    agent_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
):
    """List all registered agents with optional filters"""
    try:
        db = get_db_manager()

        with db.get_session() as session:
            from cavia_common.database import AgentRegistryModel

            query = session.query(AgentRegistryModel)

            if agent_type:
                query = query.filter_by(agent_type=agent_type)

            if status:
                query = query.filter_by(status=status)
            else:
                # Default to active agents only
                query = query.filter_by(status="active")

            agents = query.limit(limit).all()

            return [
                AgentInfo(
                    agent_id=agent.agent_id,
                    agent_type=agent.agent_type,
                    name=agent.name,
                    description=agent.description,
                    capabilities=agent.capabilities or {},
                    queue_name=agent.queue_name,
                    status=agent.status,
                )
                for agent in agents
            ]

    except Exception as e:
        logger.error("List agents error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/{agent_id}", response_model=AgentInfo)
async def get_agent(agent_id: str):
    """Get specific agent details"""
    try:
        db = get_db_manager()

        with db.get_session() as session:
            from cavia_common.database import AgentRegistryModel

            agent = (
                session.query(AgentRegistryModel)
                .filter_by(agent_id=agent_id)
                .first()
            )

            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")

            return AgentInfo(
                agent_id=agent.agent_id,
                agent_type=agent.agent_type,
                name=agent.name,
                description=agent.description,
                capabilities=agent.capabilities or {},
                queue_name=agent.queue_name,
                status=agent.status,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get agent error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/search", response_model=List[AgentInfo])
async def search_agents(request: AgentSearchRequest):
    """Semantic search for agents by capability description"""
    try:
        db = get_db_manager()

        # For now, simple text-based search
        # TODO: Implement proper vector similarity search with pgvector
        agents = db.find_agents_by_capability(request.query, limit=request.limit)

        return [
            AgentInfo(
                agent_id=a["agent_id"],
                agent_type=a["agent_type"],
                name=a["name"],
                description=a["description"],
                capabilities=a["capabilities"] or {},
                queue_name=a["queue_name"],
                status="active",
            )
            for a in agents
        ]

    except Exception as e:
        logger.error("Search error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/agents/{agent_id}")
async def deregister_agent(agent_id: str):
    """Deregister an agent (mark as inactive)"""
    try:
        db = get_db_manager()

        with db.get_session() as session:
            from cavia_common.database import AgentRegistryModel

            agent = (
                session.query(AgentRegistryModel)
                .filter_by(agent_id=agent_id)
                .first()
            )

            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")

            agent.status = "inactive"
            session.commit()

            logger.info("Agent deregistered", agent_id=agent_id)

            return {"status": "success", "message": "Agent deregistered"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Deregister error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
