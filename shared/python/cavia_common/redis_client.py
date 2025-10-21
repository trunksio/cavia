"""
Redis client and RQ queue management
"""

from typing import Any, Dict, Optional, Callable
import redis
from redis import Redis
from rq import Queue, Worker
from rq.job import Job

from .config import get_settings
from .logging import get_logger

logger = get_logger(__name__)


class RedisClient:
    """Redis connection and queue management"""

    def __init__(self, redis_url: Optional[str] = None):
        settings = get_settings()
        self.redis_url = redis_url or str(settings.redis_url)
        # RQ requires decode_responses=False - explicitly set it
        self.connection = redis.from_url(
            self.redis_url,
            decode_responses=False,
            health_check_interval=30
        )
        logger.info("Redis client initialized", redis_url=self.redis_url)

    def get_queue(self, queue_name: str) -> Queue:
        """Get or create a queue"""
        return Queue(queue_name, connection=self.connection)

    def enqueue_task(
        self,
        queue_name: str,
        func: Callable,
        *args,
        job_id: Optional[str] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> Job:
        """Enqueue a task to a specific queue"""
        queue = self.get_queue(queue_name)
        settings = get_settings()
        timeout = timeout or settings.agent_timeout

        job = queue.enqueue(
            func,
            *args,
            job_id=job_id,
            timeout=timeout,
            **kwargs,
        )
        logger.info(
            "Task enqueued",
            queue=queue_name,
            job_id=job.id,
            func=func.__name__,
        )
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        try:
            return Job.fetch(job_id, connection=self.connection)
        except Exception as e:
            logger.error("Failed to fetch job", job_id=job_id, error=str(e))
            return None

    def get_job_status(self, job_id: str) -> Optional[str]:
        """Get job status"""
        job = self.get_job(job_id)
        return job.get_status() if job else None

    def get_job_result(self, job_id: str) -> Optional[Any]:
        """Get job result"""
        job = self.get_job(job_id)
        if job and job.is_finished:
            return job.result
        return None

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        job = self.get_job(job_id)
        if job:
            job.cancel()
            logger.info("Job cancelled", job_id=job_id)
            return True
        return False

    def get_queue_length(self, queue_name: str) -> int:
        """Get number of jobs in queue"""
        queue = self.get_queue(queue_name)
        return len(queue)

    def clear_queue(self, queue_name: str) -> None:
        """Clear all jobs from queue"""
        queue = self.get_queue(queue_name)
        queue.empty()
        logger.info("Queue cleared", queue=queue_name)

    def start_worker(
        self, queue_names: list[str], name: Optional[str] = None
    ) -> Worker:
        """Start an RQ worker for specified queues"""
        queues = [self.get_queue(qname) for qname in queue_names]
        worker = Worker(queues, connection=self.connection, name=name)
        logger.info("Worker created", queues=queue_names, worker_name=name)
        return worker

    def set_value(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set a value in Redis"""
        try:
            if ttl:
                self.connection.setex(key, ttl, value)
            else:
                self.connection.set(key, value)
            return True
        except Exception as e:
            logger.error("Failed to set value", key=key, error=str(e))
            return False

    def get_value(self, key: str) -> Optional[str]:
        """Get a value from Redis"""
        try:
            return self.connection.get(key)
        except Exception as e:
            logger.error("Failed to get value", key=key, error=str(e))
            return None

    def delete_key(self, key: str) -> bool:
        """Delete a key from Redis"""
        try:
            self.connection.delete(key)
            return True
        except Exception as e:
            logger.error("Failed to delete key", key=key, error=str(e))
            return False


# Global Redis client instance
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """Get global Redis client instance"""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client
