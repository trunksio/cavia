"""
Agent Registry Router - Exposes agent information from ChromaDB registry
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import requests
import os

router = APIRouter()

# Agent registry service URL
AGENT_REGISTRY_URL = os.getenv("AGENT_REGISTRY_URL", "http://agent-registry:8000")


@router.get("/agents", response_model=List[Dict[str, Any]])
async def list_agents():
    """
    List all registered agents from the agent registry.

    Returns:
    - List of agents with their capabilities, status, and metadata
    """
    try:
        response = requests.get(f"{AGENT_REGISTRY_URL}/agents", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to agent registry: {str(e)}"
        )


@router.get("/agents/{agent_id}", response_model=Dict[str, Any])
async def get_agent(agent_id: str):
    """
    Get detailed information about a specific agent.

    Args:
    - agent_id: The unique identifier of the agent

    Returns:
    - Agent details including capabilities, status, and metadata
    """
    try:
        response = requests.get(
            f"{AGENT_REGISTRY_URL}/agents/{agent_id}",
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        if hasattr(e, 'response') and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to agent registry: {str(e)}"
        )


@router.get("/agents/discover", response_model=List[Dict[str, Any]])
async def discover_agents(capability_query: str, limit: int = 5):
    """
    Discover agents using semantic search by capability query.

    Args:
    - capability_query: Natural language description of needed capability
    - limit: Maximum number of agents to return (default: 5)

    Returns:
    - List of matching agents with similarity scores
    """
    try:
        response = requests.post(
            f"{AGENT_REGISTRY_URL}/agents/discover",
            json={"capability_query": capability_query, "limit": limit},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to agent registry: {str(e)}"
        )
