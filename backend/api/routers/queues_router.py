"""
Queues Router - Exposes RQ queue status and job information
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
import redis
import os
from rq import Queue
from rq.job import Job
from rq.registry import StartedJobRegistry, FinishedJobRegistry, FailedJobRegistry

router = APIRouter()

# Redis connection
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


def get_redis_connection():
    """Get Redis connection"""
    return redis.from_url(REDIS_URL)


@router.get("/queues", response_model=List[Dict[str, Any]])
async def list_queues():
    """
    List all RQ queues with their status.

    Returns:
    - List of queues with job counts and status
    """
    try:
        conn = get_redis_connection()
        queue_names = ['cv-parsing', 'cv-evaluation', 'cv-reporting', 'db-updates']

        queues_info = []
        for queue_name in queue_names:
            queue = Queue(queue_name, connection=conn)
            started_registry = StartedJobRegistry(queue_name, connection=conn)
            finished_registry = FinishedJobRegistry(queue_name, connection=conn)
            failed_registry = FailedJobRegistry(queue_name, connection=conn)

            queues_info.append({
                "name": queue_name,
                "queued_jobs": len(queue),
                "started_jobs": len(started_registry),
                "finished_jobs": len(finished_registry),
                "failed_jobs": len(failed_registry),
                "total_jobs": len(queue) + len(started_registry),
            })

        return queues_info
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to Redis: {str(e)}"
        )


@router.get("/queues/{queue_name}", response_model=Dict[str, Any])
async def get_queue_details(queue_name: str):
    """
    Get detailed information about a specific queue.

    Args:
    - queue_name: Name of the queue (e.g., 'cv-parsing', 'cv-evaluation')

    Returns:
    - Queue details with job lists and statistics
    """
    try:
        conn = get_redis_connection()
        queue = Queue(queue_name, connection=conn)
        started_registry = StartedJobRegistry(queue_name, connection=conn)
        finished_registry = FinishedJobRegistry(queue_name, connection=conn)
        failed_registry = FailedJobRegistry(queue_name, connection=conn)

        # Get job IDs for each status
        queued_job_ids = queue.job_ids
        started_job_ids = started_registry.get_job_ids()
        finished_job_ids = finished_registry.get_job_ids()[:20]  # Last 20
        failed_job_ids = failed_registry.get_job_ids()[:20]  # Last 20

        # Get job details
        def get_job_info(job_id: str) -> Optional[Dict[str, Any]]:
            try:
                job = Job.fetch(job_id, connection=conn)
                return {
                    "job_id": job.id,
                    "status": job.get_status(),
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "ended_at": job.ended_at.isoformat() if job.ended_at else None,
                    "func_name": job.func_name,
                    "args": str(job.args)[:100] if job.args else None,
                }
            except:
                return None

        return {
            "name": queue_name,
            "statistics": {
                "queued": len(queued_job_ids),
                "started": len(started_job_ids),
                "finished": len(finished_job_ids),
                "failed": len(failed_job_ids),
            },
            "queued_jobs": [get_job_info(jid) for jid in queued_job_ids[:20]],
            "started_jobs": [get_job_info(jid) for jid in started_job_ids],
            "finished_jobs": [get_job_info(jid) for jid in finished_job_ids],
            "failed_jobs": [get_job_info(jid) for jid in failed_job_ids],
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to get queue details: {str(e)}"
        )


@router.get("/queues/jobs/{job_id}", response_model=Dict[str, Any])
async def get_job_details(job_id: str):
    """
    Get detailed information about a specific RQ job.

    Args:
    - job_id: The RQ job ID

    Returns:
    - Job details including status, timestamps, and result
    """
    try:
        conn = get_redis_connection()
        job = Job.fetch(job_id, connection=conn)

        return {
            "job_id": job.id,
            "status": job.get_status(),
            "queue": job.origin,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
            "func_name": job.func_name,
            "args": str(job.args)[:200] if job.args else None,
            "result": str(job.result)[:500] if job.result else None,
            "exc_info": job.exc_info if job.is_failed else None,
        }
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found or error: {str(e)}"
        )
