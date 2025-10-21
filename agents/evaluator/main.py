"""
Evaluator Agent - LLM-based CV evaluation against criteria
"""

import sys
import time
import json
import re
from typing import Any, Dict

# Add shared package to path
sys.path.insert(0, "/shared")

from cavia_common import (
    BaseAgent,
    AgentTask,
    AgentTaskResult,
    EvaluationResult,
    get_logger,
    setup_logging,
    get_ollama_client,
    get_db_manager,
)

from prompts import SYSTEM_PROMPT, build_evaluation_prompt

# Setup logging
setup_logging()
logger = get_logger(__name__)


class EvaluatorAgent(BaseAgent):
    """
    Agentic Unit for evaluating CVs using LLM.

    Responsibilities:
    - Receive ParsedCV and EvaluationCriterion
    - Build evaluation prompt
    - Call Ollama LLM for evaluation
    - Parse and validate response
    - Store EvaluationResult in database
    """

    def __init__(self, agent_id: str = None):
        super().__init__(agent_id)

        # Initialize Ollama client
        self.ollama = get_ollama_client()
        self.db = get_db_manager()

        self.logger.info("EvaluatorAgent initialized", agent_id=self.agent_id)

    def get_agent_type(self) -> str:
        """Return the agent type"""
        return "evaluator"

    def get_agent_info(self) -> Dict[str, Any]:
        """Return agent metadata for registration"""
        return {
            "name": "CV Evaluator Agent",
            "description": "LLM-based evaluation of CVs against configurable criteria",
            "capabilities": {
                "evaluation_types": ["criterion-based"],
                "llm_model": self.settings.ollama_model,
                "scoring_range": "0-100",
                "output_format": "structured_json",
                "version": "1.0.0",
            },
        }

    def process_task(self, task: AgentTask) -> AgentTaskResult:
        """
        Process a CV evaluation task.

        Expected task payload:
        {
            "task_type": "evaluate_cv",
            "payload": {
                "job_id": "uuid",
                "parsed_cv": ParsedCV.dict(),
                "criterion": EvaluationCriterion.dict()
            }
        }
        """
        start_time = time.time()

        try:
            self.logger.info(
                "Starting CV evaluation",
                task_id=task.task_id,
                job_id=task.payload.get("job_id"),
                criterion=task.payload.get("criterion", {}).get("name"),
            )

            # Extract task parameters
            job_id = task.payload["job_id"]
            parsed_cv = task.payload["parsed_cv"]
            criterion = task.payload["criterion"]

            # Build evaluation prompt
            prompt = build_evaluation_prompt(parsed_cv, criterion)

            # Call LLM for evaluation
            evaluation = self._evaluate_with_llm(prompt, criterion["name"])

            # Create EvaluationResult
            eval_result = EvaluationResult(
                criterion_id=criterion["criterion_id"],
                agent_id=self.agent_id,
                score=evaluation["score"],
                confidence=evaluation["confidence"],
                evidence=evaluation["evidence"],
                reasoning=evaluation["reasoning"],
            )

            # Store in database
            self._store_evaluation(job_id, eval_result)

            execution_time = time.time() - start_time

            self.logger.info(
                "CV evaluation completed successfully",
                task_id=task.task_id,
                job_id=job_id,
                criterion=criterion["name"],
                score=eval_result.score,
                execution_time=execution_time,
            )

            return AgentTaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="success",
                result={
                    "job_id": job_id,
                    "evaluation": eval_result.dict(),
                },
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time

            self.logger.error(
                "CV evaluation failed",
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

    def _evaluate_with_llm(self, prompt: str, criterion_name: str) -> Dict[str, Any]:
        """
        Call Ollama LLM to evaluate CV.

        Args:
            prompt: Evaluation prompt
            criterion_name: Name of criterion (for logging)

        Returns:
            Dict with score, confidence, evidence, reasoning
        """
        self.logger.debug("Calling LLM for evaluation", criterion=criterion_name)

        try:
            # Call Ollama with chat interface
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]

            response = self.ollama.chat(
                messages=messages,
                temperature=0.3,  # Low temperature for consistency
            )

            if not response:
                raise ValueError("LLM returned empty response")

            # Parse JSON response
            evaluation = self._parse_llm_response(response)

            # Validate evaluation
            self._validate_evaluation(evaluation)

            return evaluation

        except Exception as e:
            self.logger.error("LLM evaluation error", error=str(e))
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
            evaluation = json.loads(json_str)
            return evaluation
        except json.JSONDecodeError as e:
            self.logger.error("Failed to parse LLM JSON response", response=response[:500])
            raise ValueError(f"Invalid JSON in LLM response: {e}")

    def _validate_evaluation(self, evaluation: Dict[str, Any]):
        """Validate evaluation dict has required fields"""
        required_fields = ["score", "confidence", "evidence", "reasoning"]

        for field in required_fields:
            if field not in evaluation:
                raise ValueError(f"Missing required field in evaluation: {field}")

        # Validate ranges
        score = evaluation["score"]
        if not isinstance(score, (int, float)) or not (0 <= score <= 100):
            raise ValueError(f"Score must be between 0-100, got: {score}")

        confidence = evaluation["confidence"]
        if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
            raise ValueError(f"Confidence must be between 0-1, got: {confidence}")

    def _store_evaluation(self, job_id: str, evaluation: EvaluationResult):
        """Store EvaluationResult in database"""
        try:
            with self.db.get_session() as session:
                from sqlalchemy import text

                query = text("""
                    INSERT INTO cv_evaluations (
                        job_id,
                        criterion_id,
                        agent_id,
                        score,
                        confidence,
                        evidence,
                        reasoning,
                        metadata
                    ) VALUES (
                        :job_id,
                        :criterion_id,
                        :agent_id,
                        :score,
                        :confidence,
                        :evidence,
                        :reasoning,
                        :metadata::jsonb
                    )
                """)

                session.execute(
                    query,
                    {
                        "job_id": job_id,
                        "criterion_id": evaluation.criterion_id,
                        "agent_id": evaluation.agent_id,
                        "score": evaluation.score,
                        "confidence": evaluation.confidence,
                        "evidence": evaluation.evidence,
                        "reasoning": evaluation.reasoning,
                        "metadata": json.dumps(evaluation.metadata),
                    }
                )
                session.commit()

            self.logger.debug("Evaluation stored in database", job_id=job_id)

        except Exception as e:
            self.logger.error("Failed to store evaluation in database", error=str(e))
            raise


def main():
    """Main entry point for the Evaluator Agent"""
    import os

    # Get agent ID from environment
    agent_id = os.getenv("AGENT_ID", "evaluator-001")

    # Create and start agent
    agent = EvaluatorAgent(agent_id=agent_id)

    logger.info(
        "Starting Evaluator Agent worker",
        agent_id=agent.agent_id,
        agent_type=agent.get_agent_type(),
    )

    # Start the RQ worker (blocking call)
    agent.start_worker()


if __name__ == "__main__":
    main()
