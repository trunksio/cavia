"""
CV Upload and Management Router
"""

import sys
import uuid
import json
from datetime import datetime
from typing import Optional
from io import BytesIO

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from pydantic import BaseModel

sys.path.insert(0, "/shared")

from cavia_common import (
    get_logger,
    get_minio_client,
    get_db_manager,
    get_redis_connection,
    AgentTask,
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
    file: UploadFile = File(..., description="CV file (PDF or DOCX)")
):
    """
    Upload a CV file and create a processing job.

    - Validates file type (PDF/DOCX only)
    - Uploads to MinIO
    - Creates job in database
    - Triggers orchestrator workflow

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

        # Enqueue directly to parser queue (skip orchestrator)
        redis_conn = get_redis_connection()
        parser_queue = Queue("cv-parsing", connection=redis_conn)

        # Create parser task with intent
        parser_task = AgentTask(
            task_id=str(uuid.uuid4()),
            task_type="parse_cv",
            payload={
                "job_id": job_id,
                "filename": file.filename,
                "minio_bucket": "cvs-raw",
                "minio_path": minio_path,
            },
            intent="Process CV and determine acceptance",
            steps_completed=[],  # Start of agent chain
        )

        # Enqueue task
        rq_job = parser_queue.enqueue(
            "cavia_common.base_agent.process_agent_task",
            parser_task.model_dump(),
            job_timeout='30m',
            result_ttl=3600,
        )

        logger.info(
            "Parser task enqueued directly (AOA)",
            job_id=job_id,
            rq_job_id=rq_job.id,
            intent=parser_task.intent,
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
