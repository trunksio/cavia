"""
Job Status and Results Router
"""

import sys
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

sys.path.insert(0, "/shared")

from cavia_common import get_logger, get_db_manager, get_minio_client

logger = get_logger(__name__)
router = APIRouter()


class JobStatus(BaseModel):
    """Job status response"""
    job_id: str
    filename: str
    status: str
    submitted_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class EvaluationDetail(BaseModel):
    """Individual evaluation result"""
    criterion_id: str
    criterion_name: str
    score: float
    confidence: float
    evidence: str
    reasoning: str
    weight: float


class JobResult(BaseModel):
    """Complete job result with report"""
    job_id: str
    filename: str
    status: str
    recommendation: Optional[str] = None
    overall_score: Optional[float] = None
    summary: Optional[str] = None
    strengths: Optional[List[str]] = None
    concerns: Optional[List[str]] = None
    detailed_analysis: Optional[str] = None
    evaluations: Optional[List[EvaluationDetail]] = None
    report_url: Optional[str] = None
    submitted_at: datetime
    completed_at: Optional[datetime] = None


@router.get("/jobs", response_model=List[JobStatus])
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List all CV processing jobs.

    Query parameters:
    - status: Filter by job status (pending, parsing, evaluating, generating_report, completed, failed)
    - limit: Maximum number of results (default: 50)
    - offset: Pagination offset (default: 0)
    """
    try:
        db = get_db_manager()

        with db.get_session() as session:
            from sqlalchemy import text

            if status:
                query = text("""
                    SELECT
                        job_id,
                        filename,
                        status,
                        submitted_at,
                        started_at,
                        completed_at,
                        error_message
                    FROM cv_jobs
                    WHERE status = :status
                    ORDER BY submitted_at DESC
                    LIMIT :limit OFFSET :offset
                """)
                results = session.execute(
                    query,
                    {"status": status, "limit": limit, "offset": offset}
                ).fetchall()
            else:
                query = text("""
                    SELECT
                        job_id,
                        filename,
                        status,
                        submitted_at,
                        started_at,
                        completed_at,
                        error_message
                    FROM cv_jobs
                    ORDER BY submitted_at DESC
                    LIMIT :limit OFFSET :offset
                """)
                results = session.execute(
                    query,
                    {"limit": limit, "offset": offset}
                ).fetchall()

            jobs = []
            for row in results:
                jobs.append(JobStatus(
                    job_id=row[0],
                    filename=row[1],
                    status=row[2],
                    submitted_at=row[3],
                    started_at=row[4],
                    completed_at=row[5],
                    error_message=row[6]
                ))

            return jobs

    except Exception as e:
        logger.error("Failed to list jobs", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve jobs: {str(e)}"
        )


@router.get("/jobs/{job_id}/status", response_model=JobStatus)
async def get_job_status(job_id: str):
    """
    Get the current status of a CV processing job.

    Returns:
    - Job status (pending, parsing, evaluating, generating_report, completed, failed)
    - Timestamps
    - Error message (if failed)
    """
    try:
        db = get_db_manager()

        with db.get_session() as session:
            from sqlalchemy import text

            query = text("""
                SELECT
                    job_id,
                    filename,
                    status,
                    submitted_at,
                    started_at,
                    completed_at,
                    error_message
                FROM cv_jobs
                WHERE job_id = :job_id
            """)

            result = session.execute(query, {"job_id": job_id}).fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="Job not found")

            return JobStatus(
                job_id=result[0],
                filename=result[1],
                status=result[2],
                submitted_at=result[3],
                started_at=result[4],
                completed_at=result[5],
                error_message=result[6]
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get job status", error=str(e), job_id=job_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve job status: {str(e)}"
        )


@router.get("/jobs/{job_id}/result", response_model=JobResult)
async def get_job_result(job_id: str):
    """
    Get the complete evaluation result for a job.

    Returns:
    - Overall recommendation (SUITABLE/REJECTED)
    - Aggregate score
    - Individual criterion evaluations
    - Report summary and analysis
    - Link to download full markdown report

    Only available when job status is 'completed'.
    """
    try:
        db = get_db_manager()

        with db.get_session() as session:
            from sqlalchemy import text

            # Get job details
            job_query = text("""
                SELECT
                    job_id,
                    filename,
                    status,
                    submitted_at,
                    completed_at,
                    metadata
                FROM cv_jobs
                WHERE job_id = :job_id
            """)

            job_result = session.execute(job_query, {"job_id": job_id}).fetchone()

            if not job_result:
                raise HTTPException(status_code=404, detail="Job not found")

            job_metadata = job_result[5] or {}

            # Check if job is completed
            if job_result[2] != "completed":
                raise HTTPException(
                    status_code=400,
                    detail=f"Job is not completed yet. Current status: {job_result[2]}"
                )

            # Extract report from metadata
            report = job_metadata.get("report", {})

            if not report:
                raise HTTPException(
                    status_code=404,
                    detail="Report not found for this job"
                )

            # Get evaluation results
            eval_query = text("""
                SELECT
                    e.criterion_id,
                    c.name,
                    e.score,
                    e.confidence,
                    e.evidence,
                    e.reasoning,
                    c.weight
                FROM cv_evaluations e
                JOIN evaluation_criteria c ON e.criterion_id = c.criterion_id
                WHERE e.job_id = :job_id
                ORDER BY c.weight DESC
            """)

            eval_results = session.execute(eval_query, {"job_id": job_id}).fetchall()

            evaluations = [
                EvaluationDetail(
                    criterion_id=row[0],
                    criterion_name=row[1],
                    score=float(row[2]),
                    confidence=float(row[3]),
                    evidence=row[4],
                    reasoning=row[5],
                    weight=float(row[6])
                )
                for row in eval_results
            ]

            # Construct report URL (if available in MinIO)
            report_url = None
            if report.get("storage_path"):
                report_url = f"/api/v1/jobs/{job_id}/report/download"

            return JobResult(
                job_id=job_result[0],
                filename=job_result[1],
                status=job_result[2],
                recommendation=report.get("recommendation"),
                overall_score=report.get("overall_score"),
                summary=report.get("summary"),
                strengths=report.get("strengths"),
                concerns=report.get("concerns"),
                detailed_analysis=report.get("detailed_analysis"),
                evaluations=evaluations,
                report_url=report_url,
                submitted_at=job_result[3],
                completed_at=job_result[4]
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get job result", error=str(e), job_id=job_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve job result: {str(e)}"
        )


@router.get("/jobs/{job_id}/report/download")
async def download_report(job_id: str):
    """
    Download the full markdown report for a completed job.

    Returns markdown file with complete evaluation report.
    """
    try:
        db = get_db_manager()

        # Verify job exists and is completed
        with db.get_session() as session:
            from sqlalchemy import text

            query = text("""
                SELECT status, filename
                FROM cv_jobs
                WHERE job_id = :job_id
            """)

            result = session.execute(query, {"job_id": job_id}).fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="Job not found")

            if result[0] != "completed":
                raise HTTPException(
                    status_code=400,
                    detail=f"Report not available. Job status: {result[0]}"
                )

            filename = result[1]

        # Download report from MinIO
        minio = get_minio_client()
        report_path = f"reports/{job_id}/report.md"

        report_data = minio.download_file("cvs-processed", report_path)

        if not report_data:
            raise HTTPException(
                status_code=404,
                detail="Report file not found in storage"
            )

        from fastapi.responses import StreamingResponse
        from io import BytesIO

        return StreamingResponse(
            BytesIO(report_data),
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="report_{job_id}.md"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to download report", error=str(e), job_id=job_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download report: {str(e)}"
        )
