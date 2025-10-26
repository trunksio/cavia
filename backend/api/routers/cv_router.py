"""
CV Upload and Management Router
"""

import sys
import uuid
import json
from datetime import datetime
from typing import Optional
from io import BytesIO

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Form
from pydantic import BaseModel
import requests

sys.path.insert(0, "/shared")

from cavia_common import (
    get_logger,
    get_minio_client,
    get_db_manager,
    get_redis_connection,
    AgentTask,
    AgentTaskV2,
    StructuredIntent,
)

from rq import Queue

logger = get_logger(__name__)
router = APIRouter()


class CVUploadResponse(BaseModel):
    """Response model for CV upload"""
    job_id: str
    filename: str
    status: str
    message: str
    created_at: datetime


class JobSubmitRequest(BaseModel):
    """Request model for submitting a job"""
    job_id: str


@router.post("/cvs/upload", response_model=CVUploadResponse)
async def upload_cv(
    file: UploadFile = File(..., description="CV file (PDF or DOCX)"),
    intent: str = Form(None, description="Processing intent (string or JSON StructuredIntent)")
):
    """
    Upload a CV file and create a processing job.

    - Validates file type (PDF/DOCX only)
    - Uploads to MinIO
    - Creates job in database
    - Routes to appropriate agent based on intent using semantic discovery

    Intent examples:
    - "Parse standard digital CV and evaluate" (default - routes to ParserAgent)
    - "Extract structured data from scanned CV with charts" (routes to OCRAgent)
    - "Process image-based resume" (routes to OCRAgent)

    Returns job_id for tracking progress.
    """
    try:
        # Validate file type
        allowed_extensions = ['.pdf', '.docx', '.doc']
        file_ext = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''

        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )

        # Generate job ID
        job_id = str(uuid.uuid4())

        logger.info(
            "CV upload started",
            job_id=job_id,
            filename=file.filename,
            content_type=file.content_type
        )

        # Read file content
        file_content = await file.read()

        # Upload to MinIO
        minio = get_minio_client()
        minio_path = f"uploads/{job_id}/{file.filename}"

        minio.upload_file(
            bucket_name="cvs-raw",
            object_name=minio_path,
            file_data=BytesIO(file_content),
            content_type=file.content_type or "application/octet-stream",
        )

        logger.info("CV uploaded to MinIO", job_id=job_id, path=minio_path)

        # Create job in database
        db = get_db_manager()
        with db.get_session() as session:
            from sqlalchemy import text

            query = text("""
                INSERT INTO cv_jobs (
                    job_id,
                    filename,
                    minio_path,
                    status,
                    metadata
                ) VALUES (
                    :job_id,
                    :filename,
                    :minio_path,
                    :status,
                    CAST(:metadata AS jsonb)
                )
            """)

            metadata_dict = {
                "minio_bucket": "cvs-raw",
                "minio_path": minio_path
            }

            session.execute(
                query,
                {
                    "job_id": job_id,
                    "filename": file.filename,
                    "minio_path": minio_path,
                    "status": "pending",
                    "metadata": json.dumps(metadata_dict),
                }
            )
            session.commit()

        logger.info("Job created in database", job_id=job_id)

        # Determine which agent to route to based on intent
        redis_conn = get_redis_connection()

        # Parse intent - support both string (legacy) and StructuredIntent (new)
        structured_intent = None
        processing_intent_str = None

        if intent:
            try:
                # Try to parse as StructuredIntent JSON
                intent_dict = json.loads(intent)
                structured_intent = StructuredIntent(**intent_dict)
                processing_intent_str = structured_intent.goal

                # Store structured intent in job metadata
                with db.get_session() as session:
                    from sqlalchemy import text
                    query = text("""
                        UPDATE cv_jobs
                        SET metadata = jsonb_set(
                            metadata,
                            '{intent}',
                            CAST(:intent_json AS jsonb)
                        )
                        WHERE job_id = :job_id
                    """)
                    session.execute(
                        query,
                        {
                            "job_id": job_id,
                            "intent_json": json.dumps(structured_intent.model_dump())
                        }
                    )
                    session.commit()

                logger.info("StructuredIntent parsed and stored", job_id=job_id, intent_id=structured_intent.intent_id)
            except (json.JSONDecodeError, Exception):
                # Fallback to string intent (legacy)
                processing_intent_str = intent
                logger.info("Using string intent (legacy)", intent=processing_intent_str)
        else:
            processing_intent_str = "Parse standard digital CV and evaluate against criteria"

        # Use semantic discovery to find the appropriate first agent
        agent_info, queue_name, task_type = _discover_agent_for_intent(processing_intent_str)

        logger.info(
            "Agent discovered for intent",
            intent=processing_intent_str,
            agent_type=agent_info.get("agent_type") if agent_info else "unknown",
            queue_name=queue_name,
        )

        # Create appropriate task type based on intent format
        if structured_intent:
            # Create AgentTaskV2 with StructuredIntent
            agent_task = AgentTaskV2(
                task_id=str(uuid.uuid4()),
                task_type=task_type,
                payload={
                    "job_id": job_id,
                    "filename": file.filename,
                    "minio_bucket": "cvs-raw",
                    "minio_path": minio_path,
                },
                intent=structured_intent,
                intent_validations=[],
                steps_completed=[],
            )
        else:
            # Create legacy AgentTask with string intent
            agent_task = AgentTask(
                task_id=str(uuid.uuid4()),
                task_type=task_type,
                payload={
                    "job_id": job_id,
                    "filename": file.filename,
                    "minio_bucket": "cvs-raw",
                    "minio_path": minio_path,
                },
                intent=processing_intent_str,
                steps_completed=[],
            )

        # Enqueue task to discovered agent's queue
        agent_queue = Queue(queue_name, connection=redis_conn)
        rq_job = agent_queue.enqueue(
            "cavia_common.base_agent.process_agent_task",
            agent_task.model_dump(),
            job_timeout='30m',
            result_ttl=3600,
        )

        logger.info(
            "Task enqueued to agent via semantic discovery",
            job_id=job_id,
            rq_job_id=rq_job.id,
            intent=processing_intent_str,
            queue=queue_name,
            agent_type=agent_info.get("agent_type") if agent_info else "unknown",
            task_version="v2" if structured_intent else "v1"
        )

        return CVUploadResponse(
            job_id=job_id,
            filename=file.filename,
            status="pending",
            message="CV uploaded successfully. Processing started.",
            created_at=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("CV upload failed", error=str(e), filename=file.filename)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload CV: {str(e)}"
        )


def _discover_agent_for_intent(intent: str) -> tuple:
    """
    Discover the appropriate agent for the given intent using semantic search.

    Args:
        intent: The user's processing intent

    Returns:
        Tuple of (agent_info, queue_name, task_type)
    """
    import os

    # Agent registry service URL
    AGENT_REGISTRY_URL = os.getenv("AGENT_REGISTRY_URL", "http://agent-registry:8000")

    try:
        # Call agent discovery endpoint
        response = requests.post(
            f"{AGENT_REGISTRY_URL}/agents/discover",
            json={"capability_query": intent, "limit": 1},
            timeout=10
        )
        response.raise_for_status()

        agents = response.json()

        if not agents or len(agents) == 0:
            logger.warning(f"No agent found for intent: {intent}, falling back to parser")
            # Fallback to parser agent
            return (
                {"agent_type": "parser", "name": "Parser Agent (fallback)"},
                "cv-parsing",
                "parse_cv"
            )

        # Get the best matching agent
        best_agent = agents[0]

        logger.info(
            "Agent discovered",
            intent=intent,
            agent_id=best_agent.get("agent_id"),
            agent_type=best_agent.get("agent_type"),
            similarity_score=best_agent.get("similarity", 0),
        )

        # Determine task type based on agent type
        task_type_map = {
            "parser": "parse_cv",
            "ocr": "extract_from_image_cv",
            "evaluator": "evaluate_cv",
            "reporter": "generate_report",
        }

        agent_type = best_agent.get("agent_type", "parser")
        task_type = task_type_map.get(agent_type, "parse_cv")
        queue_name = best_agent.get("queue_name", "cv-parsing")

        return (best_agent, queue_name, task_type)

    except Exception as e:
        logger.error(f"Agent discovery failed: {e}, falling back to parser")
        # Fallback to parser agent
        return (
            {"agent_type": "parser", "name": "Parser Agent (fallback)"},
            "cv-parsing",
            "parse_cv"
        )


@router.get("/cvs/{job_id}/download")
async def download_cv(job_id: str):
    """
    Download the original CV file for a job.

    Returns the raw CV file from MinIO.
    """
    try:
        db = get_db_manager()

        # Get job metadata
        with db.get_session() as session:
            from sqlalchemy import text

            query = text("""
                SELECT filename, metadata
                FROM cv_jobs
                WHERE job_id = :job_id
            """)

            result = session.execute(query, {"job_id": job_id}).fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="Job not found")

            filename = result[0]
            metadata = result[1]
            minio_path = metadata.get("minio_path")

            if not minio_path:
                raise HTTPException(status_code=404, detail="CV file not found")

        # Download from MinIO
        minio = get_minio_client()
        file_data = minio.download_file("cvs-raw", minio_path)

        if not file_data:
            raise HTTPException(status_code=404, detail="CV file not found in storage")

        from fastapi.responses import StreamingResponse

        return StreamingResponse(
            BytesIO(file_data),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("CV download failed", error=str(e), job_id=job_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download CV: {str(e)}"
        )


@router.get("/cvs/{job_id}/intent")
async def get_job_intent(job_id: str):
    """
    Get the structured intent for a job (if available).

    Returns the StructuredIntent that was used to initiate the workflow.
    Returns 404 if the job doesn't have a structured intent.
    """
    try:
        db = get_db_manager()

        with db.get_session() as session:
            from sqlalchemy import text

            query = text("""
                SELECT metadata
                FROM cv_jobs
                WHERE job_id = :job_id
            """)

            result = session.execute(query, {"job_id": job_id}).fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="Job not found")

            metadata = result[0]
            intent_data = metadata.get("intent")

            if not intent_data:
                raise HTTPException(
                    status_code=404,
                    detail="No structured intent found for this job"
                )

            return intent_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get job intent", error=str(e), job_id=job_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve job intent: {str(e)}"
        )


@router.get("/cvs/{job_id}/validations")
async def get_job_validations(job_id: str):
    """
    Get all intent validations for a job.

    Returns the list of IntentValidation objects from each agent in the chain.
    Returns empty list if no validations exist yet.
    """
    try:
        db = get_db_manager()

        with db.get_session() as session:
            from sqlalchemy import text

            query = text("""
                SELECT metadata
                FROM cv_jobs
                WHERE job_id = :job_id
            """)

            result = session.execute(query, {"job_id": job_id}).fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="Job not found")

            metadata = result[0]
            validations = metadata.get("intent_validations", [])

            return validations

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get job validations", error=str(e), job_id=job_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve job validations: {str(e)}"
        )
