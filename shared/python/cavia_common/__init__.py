"""
CAVIA Common - Shared utilities for Agent Oriented Architecture
"""

from .config import Settings, get_settings
from .logging import setup_logging, get_logger
from .models import (
    AgentRegistration,
    AgentStatus,
    JobStatus,
    CVJob,
    EvaluationResult,
    ParsedCV,
    EvaluationCriterion,
    CVEvaluationReport,
    AgentTask,
    AgentTaskResult,
    # Structured evaluation models for Instructor
    ReasoningStep,
    SubCriterion,
    StructuredEvaluation,
)
from .database import DatabaseManager, get_db_manager
from .redis_client import get_redis_connection
from .minio_client import MinIOClient, get_minio_client
from .ollama_client import OllamaClient, get_ollama_client
from .base_agent import BaseAgent

__version__ = "0.1.0"

__all__ = [
    "Settings",
    "get_settings",
    "setup_logging",
    "get_logger",
    "AgentRegistration",
    "AgentStatus",
    "JobStatus",
    "CVJob",
    "EvaluationResult",
    "ParsedCV",
    "EvaluationCriterion",
    "CVEvaluationReport",
    "AgentTask",
    "AgentTaskResult",
    "ReasoningStep",
    "SubCriterion",
    "StructuredEvaluation",
    "DatabaseManager",
    "get_db_manager",
    "get_redis_connection",
    "MinIOClient",
    "get_minio_client",
    "OllamaClient",
    "get_ollama_client",
    "BaseAgent",
]
