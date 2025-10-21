"""
Reporter Agent - Generates comprehensive CV evaluation reports
"""

import sys
import time
import json
import re
from typing import Any, Dict, List
from io import BytesIO

# Add shared package to path
sys.path.insert(0, "/shared")

from cavia_common import (
    BaseAgent,
    AgentTask,
    AgentTaskResult,
    CVEvaluationReport,
    get_logger,
    setup_logging,
    get_ollama_client,
    get_db_manager,
    get_minio_client,
)

from report_templates import (
    SYSTEM_PROMPT,
    build_report_prompt,
    format_markdown_report,
)

# Setup logging
setup_logging()
logger = get_logger(__name__)


class ReporterAgent(BaseAgent):
    """
    Agentic Unit for generating CV evaluation reports.

    Responsibilities:
    - Fetch evaluation results from database
    - Generate comprehensive report using LLM
    - Determine SUITABLE/REJECTED recommendation
    - Store report in database and MinIO
    - Format report as Markdown
    """

    def __init__(self, agent_id: str = None):
        super().__init__(agent_id)

        # Initialize clients
        self.ollama = get_ollama_client()
        self.db = get_db_manager()
        self.minio = get_minio_client()

        self.logger.info("ReporterAgent initialized", agent_id=self.agent_id)

    def get_agent_type(self) -> str:
        """Return the agent type"""
        return "reporter"

    def get_agent_info(self) -> Dict[str, Any]:
        """Return agent metadata for registration"""
        return {
            "name": "CV Reporter Agent",
            "description": "Generates comprehensive evaluation reports with LLM-based synthesis",
            "capabilities": {
                "report_formats": ["json", "markdown"],
                "llm_model": self.settings.ollama_model,
                "recommendation_types": ["suitable", "rejected"],
                "version": "1.0.0",
            },
        }

    def process_task(self, task: AgentTask) -> AgentTaskResult:
        """
        Process a report generation task.

        Expected task payload:
        {
            "task_type": "generate_report",
            "payload": {
                "job_id": "uuid"
            }
        }
        """
        start_time = time.time()

        try:
            self.logger.info(
                "Starting report generation",
                task_id=task.task_id,
                job_id=task.payload.get("job_id"),
            )

            # Extract task parameters
            job_id = task.payload["job_id"]

            # Fetch job data
            job_data = self._fetch_job_data(job_id)
            parsed_cv = job_data["parsed_cv"]
            criteria = job_data["criteria"]

            # Fetch evaluation results
            evaluations = self._fetch_evaluations(job_id)

            if not evaluations:
                raise ValueError("No evaluations found for job")

            # Generate report using LLM
            report_data = self._generate_report_with_llm(parsed_cv, evaluations, criteria)

            # Create CVEvaluationReport object
            candidate_name = parsed_cv.get("contact_info", {}).get("name", "Unknown")

            report = CVEvaluationReport(
                job_id=job_id,
                candidate_name=candidate_name,
                overall_score=report_data["overall_score"],
                recommendation=report_data["recommendation"],
                summary=report_data["summary"],
                strengths=report_data.get("strengths", []),
                concerns=report_data.get("concerns", []),
                detailed_analysis=report_data["rationale"],
                evaluation_results=evaluations,
            )

            # Generate markdown report
            markdown_report = format_markdown_report(
                candidate_name=candidate_name,
                report_data=report_data,
                evaluations=evaluations,
                criteria=criteria,
            )

            # Store report in database
            self._store_report(job_id, report)

            # Store markdown in MinIO
            storage_path = self._store_markdown_report(job_id, markdown_report)

            execution_time = time.time() - start_time

            self.logger.info(
                "Report generation completed successfully",
                task_id=task.task_id,
                job_id=job_id,
                recommendation=report.recommendation,
                overall_score=report.overall_score,
                execution_time=execution_time,
            )

            return AgentTaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="success",
                result={
                    "job_id": job_id,
                    "report": report.dict(),
                    "storage_path": storage_path,
                },
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time

            self.logger.error(
                "Report generation failed",
                task_id=task.task_id,
                job_id=task.payload.get("job_id"),
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

    def _fetch_job_data(self, job_id: str) -> Dict[str, Any]:
        """Fetch job data including parsed CV and criteria"""
        try:
            with self.db.get_session() as session:
                from sqlalchemy import text

                query = text("""
                    SELECT metadata
                    FROM cv_jobs
                    WHERE job_id = :job_id
                """)

                result = session.execute(query, {"job_id": job_id}).fetchone()

                if not result:
                    raise ValueError(f"Job not found: {job_id}")

                metadata = result[0]

                if "parsed_cv" not in metadata:
                    raise ValueError("ParsedCV not found in job metadata")

                # Fetch criteria from evaluation_criteria table
                criteria_query = text("""
                    SELECT criterion_id, name, description, evaluation_prompt, weight, metadata
                    FROM evaluation_criteria
                    WHERE is_active = true
                    ORDER BY weight DESC
                """)

                criteria_results = session.execute(criteria_query).fetchall()

                criteria = [
                    {
                        "criterion_id": row[0],
                        "name": row[1],
                        "description": row[2],
                        "evaluation_prompt": row[3],
                        "weight": float(row[4]),
                        "metadata": row[5],
                    }
                    for row in criteria_results
                ]

                return {
                    "parsed_cv": metadata["parsed_cv"],
                    "criteria": criteria,
                }

        except Exception as e:
            self.logger.error("Failed to fetch job data", job_id=job_id, error=str(e))
            raise

    def _fetch_evaluations(self, job_id: str) -> List[Dict[str, Any]]:
        """Fetch all evaluation results for the job"""
        try:
            with self.db.get_session() as session:
                from sqlalchemy import text

                query = text("""
                    SELECT
                        criterion_id,
                        agent_id,
                        score,
                        confidence,
                        evidence,
                        reasoning,
                        metadata
                    FROM cv_evaluations
                    WHERE job_id = :job_id
                    ORDER BY created_at ASC
                """)

                results = session.execute(query, {"job_id": job_id}).fetchall()

                evaluations = [
                    {
                        "criterion_id": row[0],
                        "agent_id": row[1],
                        "score": float(row[2]),
                        "confidence": float(row[3]),
                        "evidence": row[4],
                        "reasoning": row[5],
                        "metadata": row[6] or {},
                    }
                    for row in results
                ]

                return evaluations

        except Exception as e:
            self.logger.error("Failed to fetch evaluations", job_id=job_id, error=str(e))
            raise

    def _generate_report_with_llm(
        self,
        parsed_cv: dict,
        evaluations: List[Dict[str, Any]],
        criteria: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate report using LLM.

        Args:
            parsed_cv: ParsedCV as dict
            evaluations: List of EvaluationResult dicts
            criteria: List of EvaluationCriterion dicts

        Returns:
            Dict with recommendation, overall_score, summary, strengths, concerns, rationale
        """
        self.logger.debug("Calling LLM for report generation")

        try:
            # Build report prompt
            prompt = build_report_prompt(parsed_cv, evaluations, criteria)

            # Call Ollama
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]

            response = self.ollama.chat(
                messages=messages,
                temperature=0.4,  # Slightly higher for more natural language
            )

            if not response:
                raise ValueError("LLM returned empty response")

            # Parse JSON response
            report_data = self._parse_llm_response(response)

            # Validate report
            self._validate_report(report_data)

            return report_data

        except Exception as e:
            self.logger.error("LLM report generation error", error=str(e))
            raise

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON response from LLM.

        Handles cases where LLM wraps JSON in markdown code blocks.
        """
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON
            json_match = re.search(r'(\{.*\})', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response

        try:
            report_data = json.loads(json_str)
            return report_data
        except json.JSONDecodeError as e:
            self.logger.error("Failed to parse LLM JSON response", response=response[:500])
            raise ValueError(f"Invalid JSON in LLM response: {e}")

    def _validate_report(self, report_data: Dict[str, Any]):
        """Validate report dict has required fields"""
        required_fields = [
            "recommendation",
            "overall_score",
            "summary",
            "strengths",
            "concerns",
            "rationale"
        ]

        for field in required_fields:
            if field not in report_data:
                raise ValueError(f"Missing required field in report: {field}")

        # Validate recommendation
        if report_data["recommendation"] not in ["SUITABLE", "REJECTED"]:
            raise ValueError(f"Invalid recommendation: {report_data['recommendation']}")

        # Validate overall_score
        score = report_data["overall_score"]
        if not isinstance(score, (int, float)) or not (0 <= score <= 100):
            raise ValueError(f"Overall score must be between 0-100, got: {score}")

    def _store_report(self, job_id: str, report: CVEvaluationReport):
        """Store report in database"""
        try:
            with self.db.get_session() as session:
                from sqlalchemy import text

                query = text("""
                    UPDATE cv_jobs
                    SET metadata = jsonb_set(
                        COALESCE(metadata, '{}'),
                        '{report}',
                        :report::jsonb
                    )
                    WHERE job_id = :job_id
                """)

                session.execute(
                    query,
                    {
                        "job_id": job_id,
                        "report": report.model_dump_json(),
                    }
                )
                session.commit()

            self.logger.debug("Report stored in database", job_id=job_id)

        except Exception as e:
            self.logger.error("Failed to store report in database", error=str(e))
            raise

    def _store_markdown_report(self, job_id: str, markdown: str) -> str:
        """Store markdown report in MinIO"""
        try:
            storage_path = f"reports/{job_id}/report.md"

            # Upload to MinIO
            self.minio.upload_file(
                bucket_name="cvs-processed",
                object_name=storage_path,
                file_data=BytesIO(markdown.encode('utf-8')),
                content_type="text/markdown",
            )

            self.logger.debug("Markdown report stored in MinIO", storage_path=storage_path)
            return storage_path

        except Exception as e:
            self.logger.error("Failed to store markdown report in MinIO", error=str(e))
            raise


def main():
    """Main entry point for the Reporter Agent"""
    import os

    # Get agent ID from environment
    agent_id = os.getenv("AGENT_ID", "reporter-001")

    # Create and start agent
    agent = ReporterAgent(agent_id=agent_id)

    logger.info(
        "Starting Reporter Agent worker",
        agent_id=agent.agent_id,
        agent_type=agent.get_agent_type(),
    )

    # Start the RQ worker (blocking call)
    agent.start_worker()


if __name__ == "__main__":
    main()
