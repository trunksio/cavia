"""
Orchestrator Agent - Coordinates CV processing workflow
"""

import sys
import time
import json
from typing import Any, Dict, List
from datetime import datetime

# Add shared package to path
sys.path.insert(0, "/shared")

from cavia_common import (
    BaseAgent,
    AgentTask,
    AgentTaskResult,
    get_logger,
    setup_logging,
    get_db_manager,
    get_redis_client,
)

from workflow import WorkflowManager, JobState

# Setup logging
setup_logging()
logger = get_logger(__name__)


class OrchestratorAgent(BaseAgent):
    """
    Agentic Unit for orchestrating CV processing workflow.

    Responsibilities:
    - Manage job state machines
    - Coordinate tasks between Parser, Evaluator, and Reporter agents
    - Track evaluation progress (3 criteria per CV)
    - Handle errors and retries
    - Update database with job status
    """

    def __init__(self, agent_id: str = None):
        super().__init__(agent_id)

        # Initialize workflow manager
        self.workflow_manager = WorkflowManager()

        # Initialize clients
        self.db = get_db_manager()
        self.redis = get_redis_client()

        self.logger.info("OrchestratorAgent initialized", agent_id=self.agent_id)

    def get_agent_type(self) -> str:
        """Return the agent type"""
        return "orchestrator"

    def get_agent_info(self) -> Dict[str, Any]:
        """Return agent metadata for registration"""
        return {
            "name": "CV Orchestrator Agent",
            "description": "Coordinates workflow between Parser, Evaluator, and Reporter agents",
            "capabilities": {
                "workflow_management": True,
                "task_coordination": True,
                "state_tracking": True,
                "error_handling": True,
                "version": "1.0.0",
            },
        }

    def process_task(self, task: AgentTask) -> AgentTaskResult:
        """
        Process an orchestration task.

        Expected task types:
        1. "start_cv_job" - Initiate CV processing workflow
        2. "parser_complete" - Handle parser completion
        3. "evaluator_complete" - Handle evaluator completion
        4. "reporter_complete" - Handle reporter completion
        """
        start_time = time.time()

        try:
            task_type = task.task_type
            job_id = task.payload.get("job_id")

            self.logger.info(
                "Processing orchestration task",
                task_id=task.task_id,
                task_type=task_type,
                job_id=job_id,
            )

            # Route to appropriate handler
            if task_type == "start_cv_job":
                result = self._handle_start_job(task)
            elif task_type == "parser_complete":
                result = self._handle_parser_complete(task)
            elif task_type == "evaluator_complete":
                result = self._handle_evaluator_complete(task)
            elif task_type == "reporter_complete":
                result = self._handle_reporter_complete(task)
            else:
                raise ValueError(f"Unknown task type: {task_type}")

            execution_time = time.time() - start_time

            self.logger.info(
                "Orchestration task completed",
                task_id=task.task_id,
                task_type=task_type,
                job_id=job_id,
                execution_time=execution_time,
            )

            return AgentTaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="success",
                result=result,
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time

            self.logger.error(
                "Orchestration task failed",
                task_id=task.task_id,
                error=str(e),
                execution_time=execution_time,
            )

            return AgentTaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="error",
                error=str(e),
                execution_time=execution_time,
            )

    def _handle_start_job(self, task: AgentTask) -> Dict[str, Any]:
        """
        Start a new CV processing job.

        Payload:
        {
            "job_id": "uuid",
            "filename": "cv.pdf",
            "minio_bucket": "cvs-raw",
            "minio_path": "path/to/cv.pdf",
            "evaluation_criteria": [criterion1, criterion2, criterion3]
        }
        """
        job_id = task.payload["job_id"]
        filename = task.payload["filename"]
        minio_bucket = task.payload["minio_bucket"]
        minio_path = task.payload["minio_path"]
        criteria = task.payload["evaluation_criteria"]

        self.logger.info(
            "Starting CV job",
            job_id=job_id,
            filename=filename,
            criteria_count=len(criteria),
        )

        # Create workflow
        workflow = self.workflow_manager.create_workflow(job_id)

        # Update job status to parsing
        self._update_job_status(job_id, JobState.PARSING)
        workflow.start_parsing()

        # Enqueue parser task
        from rq import Queue
        parser_queue = Queue("cv-parsing", connection=self.redis)

        import uuid
        parser_task = AgentTask(
            task_id=str(uuid.uuid4()),
            task_type="parse_cv",
            payload={
                "job_id": job_id,
                "filename": filename,
                "minio_bucket": minio_bucket,
                "minio_path": minio_path,
            }
        )

        parser_job = parser_queue.enqueue(
            "cavia_common.base_agent.process_agent_task",
            parser_task.dict(),
            job_timeout='10m',
            result_ttl=3600,
        )

        self.logger.info(
            "Parser task enqueued",
            job_id=job_id,
            parser_job_id=parser_job.id,
        )

        # Store criteria for later evaluation
        workflow.metadata["criteria"] = [c.dict() if hasattr(c, 'dict') else c for c in criteria]
        workflow.metadata["parser_job_id"] = parser_job.id

        return {
            "job_id": job_id,
            "state": workflow.state,
            "parser_job_id": parser_job.id,
        }

    def _handle_parser_complete(self, task: AgentTask) -> Dict[str, Any]:
        """
        Handle parser completion and start evaluations.

        Payload:
        {
            "job_id": "uuid",
            "parsed_cv": ParsedCV.dict(),
            "storage_path": "cvs-processed/parsed/..."
        }
        """
        job_id = task.payload["job_id"]
        parsed_cv = task.payload["parsed_cv"]

        self.logger.info("Parser completed", job_id=job_id)

        # Get workflow
        workflow = self.workflow_manager.get_workflow(job_id)
        if not workflow:
            raise ValueError(f"Workflow not found for job: {job_id}")

        # Update to evaluating state
        self._update_job_status(job_id, JobState.EVALUATING)
        workflow.complete_parsing()

        # Enqueue evaluation tasks (one per criterion)
        from rq import Queue
        evaluator_queue = Queue("cv-evaluation", connection=self.redis)

        criteria = workflow.metadata.get("criteria", [])
        evaluation_job_ids = []

        for criterion in criteria:
            import uuid
            eval_task = AgentTask(
                task_id=str(uuid.uuid4()),
                task_type="evaluate_cv",
                payload={
                    "job_id": job_id,
                    "parsed_cv": parsed_cv,
                    "criterion": criterion,
                }
            )

            eval_job = evaluator_queue.enqueue(
                "cavia_common.base_agent.process_agent_task",
                eval_task.dict(),
                job_timeout='15m',
                result_ttl=3600,
            )

            evaluation_job_ids.append(eval_job.id)

            self.logger.info(
                "Evaluation task enqueued",
                job_id=job_id,
                criterion=criterion.get("name"),
                eval_job_id=eval_job.id,
            )

        # Store evaluation tracking
        workflow.metadata["evaluation_job_ids"] = evaluation_job_ids
        workflow.metadata["evaluations_completed"] = 0
        workflow.metadata["evaluations_total"] = len(criteria)

        return {
            "job_id": job_id,
            "state": workflow.state,
            "evaluation_job_ids": evaluation_job_ids,
            "evaluations_total": len(criteria),
        }

    def _handle_evaluator_complete(self, task: AgentTask) -> Dict[str, Any]:
        """
        Handle evaluator completion.

        When all evaluations are complete, trigger reporter.

        Payload:
        {
            "job_id": "uuid",
            "evaluation": EvaluationResult.dict()
        }
        """
        job_id = task.payload["job_id"]
        evaluation = task.payload["evaluation"]

        self.logger.info(
            "Evaluator completed",
            job_id=job_id,
            criterion_id=evaluation.get("criterion_id"),
        )

        # Get workflow
        workflow = self.workflow_manager.get_workflow(job_id)
        if not workflow:
            raise ValueError(f"Workflow not found for job: {job_id}")

        # Increment completed count
        workflow.metadata["evaluations_completed"] += 1
        completed = workflow.metadata["evaluations_completed"]
        total = workflow.metadata["evaluations_total"]

        self.logger.info(
            "Evaluation progress",
            job_id=job_id,
            completed=completed,
            total=total,
        )

        # Check if all evaluations are complete
        if completed >= total:
            self.logger.info("All evaluations complete, starting report generation", job_id=job_id)

            # Update to generating_report state
            self._update_job_status(job_id, JobState.GENERATING_REPORT)
            workflow.complete_evaluation()

            # Enqueue reporter task
            from rq import Queue
            reporter_queue = Queue("cv-reporting", connection=self.redis)

            import uuid
            reporter_task = AgentTask(
                task_id=str(uuid.uuid4()),
                task_type="generate_report",
                payload={
                    "job_id": job_id,
                }
            )

            reporter_job = reporter_queue.enqueue(
                "cavia_common.base_agent.process_agent_task",
                reporter_task.dict(),
                job_timeout='10m',
                result_ttl=3600,
            )

            workflow.metadata["reporter_job_id"] = reporter_job.id

            self.logger.info(
                "Reporter task enqueued",
                job_id=job_id,
                reporter_job_id=reporter_job.id,
            )

            return {
                "job_id": job_id,
                "state": workflow.state,
                "reporter_job_id": reporter_job.id,
            }

        return {
            "job_id": job_id,
            "state": workflow.state,
            "evaluations_completed": completed,
            "evaluations_total": total,
        }

    def _handle_reporter_complete(self, task: AgentTask) -> Dict[str, Any]:
        """
        Handle reporter completion and mark job as complete.

        Payload:
        {
            "job_id": "uuid",
            "report": CVEvaluationReport.dict(),
            "storage_path": "reports/..."
        }
        """
        job_id = task.payload["job_id"]

        self.logger.info("Reporter completed", job_id=job_id)

        # Get workflow
        workflow = self.workflow_manager.get_workflow(job_id)
        if not workflow:
            raise ValueError(f"Workflow not found for job: {job_id}")

        # Update to completed state
        self._update_job_status(job_id, JobState.COMPLETED, completed_at=datetime.utcnow())
        workflow.complete_report()

        self.logger.info("CV job completed successfully", job_id=job_id)

        # Clean up workflow (optional - could keep for debugging)
        # self.workflow_manager.remove_workflow(job_id)

        return {
            "job_id": job_id,
            "state": workflow.state,
        }

    def _update_job_status(
        self,
        job_id: str,
        status: JobState,
        error_message: str = None,
        completed_at: datetime = None
    ):
        """Update job status in database"""
        try:
            with self.db.get_session() as session:
                from sqlalchemy import text

                if completed_at:
                    query = text("""
                        UPDATE cv_jobs
                        SET status = :status,
                            completed_at = :completed_at
                        WHERE job_id = :job_id
                    """)
                    session.execute(query, {
                        "job_id": job_id,
                        "status": status.value,
                        "completed_at": completed_at,
                    })
                elif error_message:
                    query = text("""
                        UPDATE cv_jobs
                        SET status = :status,
                            metadata = jsonb_set(
                                COALESCE(metadata, '{}'),
                                '{error_message}',
                                :error_message::jsonb
                            )
                        WHERE job_id = :job_id
                    """)
                    session.execute(query, {
                        "job_id": job_id,
                        "status": status.value,
                        "error_message": json.dumps(error_message),
                    })
                else:
                    query = text("""
                        UPDATE cv_jobs
                        SET status = :status
                        WHERE job_id = :job_id
                    """)
                    session.execute(query, {
                        "job_id": job_id,
                        "status": status.value,
                    })

                session.commit()

            self.logger.debug("Job status updated", job_id=job_id, status=status.value)

        except Exception as e:
            self.logger.error("Failed to update job status", job_id=job_id, error=str(e))
            raise


def main():
    """Main entry point for the Orchestrator Agent"""
    import os

    # Get agent ID from environment
    agent_id = os.getenv("AGENT_ID", "orchestrator-001")

    # Create and start agent
    agent = OrchestratorAgent(agent_id=agent_id)

    logger.info(
        "Starting Orchestrator Agent worker",
        agent_id=agent.agent_id,
        agent_type=agent.get_agent_type(),
    )

    # Start the RQ worker (blocking call)
    agent.start_worker()


if __name__ == "__main__":
    main()
