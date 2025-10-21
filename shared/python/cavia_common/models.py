"""
Shared data models for CAVIA
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Agent status enumeration"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    STARTING = "starting"
    STOPPING = "stopping"


class JobStatus(str, Enum):
    """CV job status enumeration"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    ACCEPTED = "accepted"


class AgentRegistration(BaseModel):
    """Agent registration model"""

    agent_id: str
    agent_type: str
    name: str
    description: str
    capabilities: Dict[str, Any]
    queue_name: str
    status: AgentStatus = AgentStatus.STARTING
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentHeartbeat(BaseModel):
    """Agent heartbeat model"""

    agent_id: str
    status: AgentStatus
    metadata: Optional[Dict[str, Any]] = None


class CVJob(BaseModel):
    """CV processing job model"""

    job_id: str
    filename: str
    minio_path: str
    status: JobStatus = JobStatus.PENDING
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ParsedCV(BaseModel):
    """Parsed CV data structure"""

    contact_info: Dict[str, str] = Field(default_factory=dict)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    experience: List[Dict[str, Any]] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    certifications: List[Dict[str, Any]] = Field(default_factory=list)
    raw_text: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvaluationCriterion(BaseModel):
    """Evaluation criterion definition"""

    criterion_id: str
    name: str
    description: str
    evaluation_prompt: str
    weight: float = 1.0
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    """Single criterion evaluation result"""

    criterion_id: str
    agent_id: str
    score: float = Field(..., ge=0, le=100, description="Score from 0 to 100")
    confidence: float = Field(..., ge=0, le=1, description="Confidence from 0 to 1")
    evidence: str
    reasoning: str
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CVEvaluationReport(BaseModel):
    """Complete CV evaluation report"""

    job_id: str
    filename: str
    parsed_cv: ParsedCV
    evaluations: List[EvaluationResult]
    overall_score: float
    decision: str  # "accept" or "reject"
    decision_reasoning: str
    rejection_reasons: Optional[List[str]] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentTask(BaseModel):
    """Task model for agent queue"""

    task_id: str
    task_type: str
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentTaskResult(BaseModel):
    """Result from agent task execution"""

    task_id: str
    agent_id: str
    status: str  # "success" or "error"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    completed_at: datetime = Field(default_factory=datetime.utcnow)
