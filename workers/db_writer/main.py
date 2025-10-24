"""
DB Writer Worker - Non-Agentic Unit for database updates

This is a simple RQ worker that handles database writes.
It's NOT an Agentic Unit - it exists at the boundary between
the event-driven agent system and the database for UI access.
"""

import sys
import json
import time
from typing import Any, Dict

# Add shared package to path
sys.path.insert(0, "/shared")

from cavia_common import (
    get_logger,
    setup_logging,
    get_db_manager,
    get_redis_connection,
)

from rq import Queue, Worker

# Setup logging
setup_logging()
logger = get_logger(__name__)


def process_db_task(task_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a database update task.

    This is the main entry point called by RQ workers.

    Expected task_dict:
    {
        "task_id": "uuid",
        "task_type": "update_job_result",
        "payload": {
            "job_id": "uuid",
            "status": "completed" | "failed",
            "result": {...}
        },
        "intent": "original intent",
        "steps_completed": ["parser", "evaluator", "reporter"]
    }
    """
    start_time = time.time()

    try:
        task_id = task_dict.get("task_id", "unknown")
        task_type = task_dict.get("task_type", "unknown")
        payload = task_dict.get("payload", {})

        logger.info(
            "Processing DB task",
            task_id=task_id,
            task_type=task_type,
            job_id=payload.get("job_id"),
        )

        if task_type == "update_job_result":
            result = update_job_result(payload)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

        execution_time = time.time() - start_time

        logger.info(
            "DB task completed successfully",
            task_id=task_id,
            task_type=task_type,
            execution_time=execution_time,
        )

        return {
            "task_id": task_id,
            "status": "success",
            "result": result,
            "execution_time": execution_time,
        }

    except Exception as e:
        execution_time = time.time() - start_time

        logger.error(
            "DB task failed",
            task_id=task_dict.get("task_id", "unknown"),
            error=str(e),
            execution_time=execution_time,
        )

        return {
            "task_id": task_dict.get("task_id", "unknown"),
            "status": "error",
            "error": str(e),
            "execution_time": execution_time,
        }


def update_job_result(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update cv_jobs table with final result.

    Expected payload:
    {
        "job_id": "uuid",
        "status": "completed" | "failed",
        "result": {
            "overall_score": 75.5,
            "decision": "SUITABLE" | "REJECTED",
            "decision_reasoning": "...",
            "summary": "...",
            "strengths": [...],
            "concerns": [...],
            "markdown_path": "..."
        }
    }
    """
    db = get_db_manager()

    job_id = payload["job_id"]
    status = payload["status"]
    result = payload.get("result", {})

    try:
        with db.get_session() as session:
            from sqlalchemy import text

            # Update cv_jobs with final result
            result_json = json.dumps(result)
            query = text("""
                UPDATE cv_jobs
                SET
                    status = :status,
                    completed_at = NOW(),
                    result = CAST(:result AS jsonb),
                    metadata = jsonb_set(
                        COALESCE(metadata, '{}'),
                        '{report}',
                        CAST(:result AS jsonb)
                    )
                WHERE job_id = :job_id
            """)

            session.execute(
                query,
                {
                    "job_id": job_id,
                    "status": status,
                    "result": result_json,
                }
            )
            session.commit()

        logger.info(
            "Job result updated in database",
            job_id=job_id,
            status=status,
            decision=result.get("decision"),
            overall_score=result.get("overall_score"),
        )

        return {
            "job_id": job_id,
            "status": status,
            "updated": True,
        }

    except Exception as e:
        logger.error("Failed to update job result", job_id=job_id, error=str(e))
        raise


def main():
    """Main entry point for the DB Writer worker"""
    logger.info("Starting DB Writer worker")

    # Get Redis connection
    redis_conn = get_redis_connection()

    # Create queue and worker
    queue = Queue("db-writer", connection=redis_conn)
    worker = Worker([queue], connection=redis_conn, name="db-writer-001")

    logger.info("DB Writer worker ready", queue="db-writer")

    # Start worker (blocking call)
    worker.work()


if __name__ == "__main__":
    main()
