"""
Agent Registry Service - Central discovery and registration for Agentic Units
Uses ChromaDB for vector storage and semantic search
"""

import sys
from contextlib import asynccontextmanager
from typing import List, Optional

sys.path.insert(0, "/shared")

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
from chromadb.config import Settings as ChromaSettings

from cavia_common import (
    get_settings,
    setup_logging,
    get_logger,
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


class AgentDiscoverRequest(BaseModel):
    capability_query: str
    limit: int = 1


class AgentDiscoverResponse(BaseModel):
    agent_id: str
    agent_type: str
    name: str
    description: str
    queue_name: str
    similarity_score: float


class AgentInfo(BaseModel):
    agent_id: str
    agent_type: str
    name: str
    description: str
    capabilities: dict
    queue_name: str
    status: str


# Global ChromaDB client and collection
chroma_client: Optional[chromadb.Client] = None
agent_collection: Optional[chromadb.Collection] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    global chroma_client, agent_collection

    # Startup
    logger.info("Starting Agent Registry Service with ChromaDB")

    # Initialize ChromaDB with persistent storage
    chroma_client = chromadb.PersistentClient(
        path="/data/chromadb",
        settings=ChromaSettings(
            anonymized_telemetry=False,
            allow_reset=True,
        )
    )

    # Get or create collection for agents
    agent_collection = chroma_client.get_or_create_collection(
        name="cavia_agents",
        metadata={"description": "CAVIA Agentic Units Registry"}
    )

    logger.info("ChromaDB initialized", collection="cavia_agents")

    yield

    # Shutdown
    logger.info("Shutting down Agent Registry Service")


# Create FastAPI app
app = FastAPI(
    title="CAVIA Agent Registry",
    description="Central registry and discovery service for Agentic Units (ChromaDB)",
    version="0.2.0",
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
        "version": "0.2.0",
        "backend": "chromadb",
    }


@app.post("/agents/register", status_code=201)
async def register_agent(request: AgentRegisterRequest):
    """
    Register a new agent or update existing registration.

    ChromaDB automatically handles embedding generation for the description.
    """
    try:
        # Build full description for embedding
        full_description = f"{request.name}: {request.description}"

        # Prepare metadata
        metadata = {
            "agent_id": request.agent_id,
            "agent_type": request.agent_type,
            "name": request.name,
            "description": request.description,
            "queue_name": request.queue_name,
            "status": "active",
            # Store capabilities as JSON string (ChromaDB metadata must be primitives)
            "capabilities": str(request.capabilities),
        }

        # Add or update in ChromaDB
        # ChromaDB uses upsert semantics - will update if ID exists
        agent_collection.upsert(
            ids=[request.agent_id],
            documents=[full_description],
            metadatas=[metadata],
        )

        logger.info("Agent registered in ChromaDB", agent_id=request.agent_id)

        return {
            "status": "success",
            "agent_id": request.agent_id,
            "message": "Agent registered successfully",
        }

    except Exception as e:
        logger.error("Registration error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/discover", response_model=List[AgentDiscoverResponse])
async def discover_agents(request: AgentDiscoverRequest):
    """
    Discover agents by semantic similarity to capability query.

    This is the key endpoint that agents call to find the next agent in the chain.
    ChromaDB automatically generates embeddings and performs vector search.
    """
    try:
        # Query ChromaDB with natural language capability description
        # ChromaDB handles embedding generation internally
        results = agent_collection.query(
            query_texts=[request.capability_query],
            n_results=request.limit,
            where={"status": "active"},  # Only active agents
        )

        # Extract results
        discovered_agents = []
        if results['ids'] and results['ids'][0]:
            for i, agent_id in enumerate(results['ids'][0]):
                metadata = results['metadatas'][0][i]
                # ChromaDB returns distances, convert to similarity (1 - distance)
                distance = results['distances'][0][i] if results['distances'] else 0
                similarity = 1.0 - distance

                discovered_agents.append(
                    AgentDiscoverResponse(
                        agent_id=metadata['agent_id'],
                        agent_type=metadata['agent_type'],
                        name=metadata['name'],
                        description=metadata['description'],
                        queue_name=metadata['queue_name'],
                        similarity_score=similarity,
                    )
                )

        logger.info(
            "Agent discovery completed",
            query=request.capability_query,
            results_count=len(discovered_agents),
        )

        return discovered_agents

    except Exception as e:
        logger.error("Discovery error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/heartbeat")
async def agent_heartbeat(agent_id: str):
    """
    Update agent heartbeat.

    Note: ChromaDB doesn't have built-in heartbeat tracking.
    We update the metadata timestamp.
    """
    try:
        # Get current agent
        result = agent_collection.get(ids=[agent_id])

        if not result['ids']:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Update metadata with new timestamp
        import time
        metadata = result['metadatas'][0]
        metadata['last_heartbeat'] = str(time.time())

        agent_collection.update(
            ids=[agent_id],
            metadatas=[metadata],
        )

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
        # Build where filter
        where_filter = {}
        if agent_type:
            where_filter["agent_type"] = agent_type
        if status:
            where_filter["status"] = status
        else:
            where_filter["status"] = "active"

        # Get from ChromaDB
        results = agent_collection.get(
            where=where_filter if where_filter else None,
            limit=limit,
        )

        agents = []
        if results['ids']:
            for i, agent_id in enumerate(results['ids']):
                metadata = results['metadatas'][i]
                # Parse capabilities back from string
                import ast
                capabilities = ast.literal_eval(metadata.get('capabilities', '{}'))

                agents.append(
                    AgentInfo(
                        agent_id=metadata['agent_id'],
                        agent_type=metadata['agent_type'],
                        name=metadata['name'],
                        description=metadata['description'],
                        capabilities=capabilities,
                        queue_name=metadata['queue_name'],
                        status=metadata.get('status', 'active'),
                    )
                )

        return agents

    except Exception as e:
        logger.error("List agents error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/{agent_id}", response_model=AgentInfo)
async def get_agent(agent_id: str):
    """Get specific agent details"""
    try:
        result = agent_collection.get(ids=[agent_id])

        if not result['ids']:
            raise HTTPException(status_code=404, detail="Agent not found")

        metadata = result['metadatas'][0]

        # Parse capabilities back from string
        import ast
        capabilities = ast.literal_eval(metadata.get('capabilities', '{}'))

        return AgentInfo(
            agent_id=metadata['agent_id'],
            agent_type=metadata['agent_type'],
            name=metadata['name'],
            description=metadata['description'],
            capabilities=capabilities,
            queue_name=metadata['queue_name'],
            status=metadata.get('status', 'active'),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get agent error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/agents/{agent_id}")
async def deregister_agent(agent_id: str):
    """Deregister an agent (mark as inactive)"""
    try:
        result = agent_collection.get(ids=[agent_id])

        if not result['ids']:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Update status to inactive
        metadata = result['metadatas'][0]
        metadata['status'] = 'inactive'

        agent_collection.update(
            ids=[agent_id],
            metadatas=[metadata],
        )

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
