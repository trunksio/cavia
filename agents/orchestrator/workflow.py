"""
Workflow state machine for CV processing jobs
"""

from enum import Enum
from typing import Dict, Any, Optional
from transitions import Machine


class JobState(str, Enum):
    """Job states in the CV processing workflow"""
    PENDING = "pending"
    PARSING = "parsing"
    EVALUATING = "evaluating"
    GENERATING_REPORT = "generating_report"
    COMPLETED = "completed"
    FAILED = "failed"


class CVJobWorkflow:
    """
    State machine for CV processing workflow.

    Workflow states:
    1. pending -> parsing (submit CV)
    2. parsing -> evaluating (CV parsed)
    3. evaluating -> generating_report (all evaluations complete)
    4. generating_report -> completed (report generated)
    5. * -> failed (any error)
    """

    # Define valid state transitions
    transitions = [
        {'trigger': 'start_parsing', 'source': JobState.PENDING.value, 'dest': JobState.PARSING.value},
        {'trigger': 'complete_parsing', 'source': JobState.PARSING.value, 'dest': JobState.EVALUATING.value},
        {'trigger': 'complete_evaluation', 'source': JobState.EVALUATING.value, 'dest': JobState.GENERATING_REPORT.value},
        {'trigger': 'complete_report', 'source': JobState.GENERATING_REPORT.value, 'dest': JobState.COMPLETED.value},
        {'trigger': 'mark_failed', 'source': '*', 'dest': JobState.FAILED.value},
    ]

    def __init__(self, job_id: str, initial_state: JobState = JobState.PENDING):
        """
        Initialize workflow state machine.

        Args:
            job_id: Unique job identifier
            initial_state: Starting state (default: PENDING)
        """
        self.job_id = job_id
        self.state = initial_state
        self.error_message: Optional[str] = None
        self.metadata: Dict[str, Any] = {}

        # Initialize state machine
        self.machine = Machine(
            model=self,
            states=[s.value for s in JobState],
            transitions=self.transitions,
            initial=initial_state.value,
            auto_transitions=False,  # Only allow defined transitions
        )

    def can_transition_to(self, target_state: JobState) -> bool:
        """Check if transition to target state is valid"""
        if target_state == JobState.FAILED:
            return True  # Can always transition to failed

        valid_transitions = {
            JobState.PENDING: [JobState.PARSING],
            JobState.PARSING: [JobState.EVALUATING],
            JobState.EVALUATING: [JobState.GENERATING_REPORT],
            JobState.GENERATING_REPORT: [JobState.COMPLETED],
        }

        current = JobState(self.state)
        return target_state in valid_transitions.get(current, [])

    def get_next_state(self) -> Optional[JobState]:
        """Get the next expected state in the workflow"""
        state_progression = {
            JobState.PENDING: JobState.PARSING,
            JobState.PARSING: JobState.EVALUATING,
            JobState.EVALUATING: JobState.GENERATING_REPORT,
            JobState.GENERATING_REPORT: JobState.COMPLETED,
            JobState.COMPLETED: None,
            JobState.FAILED: None,
        }

        current = JobState(self.state)
        return state_progression.get(current)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize workflow state"""
        return {
            "job_id": self.job_id,
            "state": self.state,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CVJobWorkflow':
        """Deserialize workflow state"""
        workflow = cls(
            job_id=data["job_id"],
            initial_state=JobState(data["state"])
        )
        workflow.error_message = data.get("error_message")
        workflow.metadata = data.get("metadata", {})
        return workflow


class WorkflowManager:
    """
    Manages workflow instances for multiple jobs.

    Responsibilities:
    - Create new workflows
    - Track workflow states
    - Validate state transitions
    """

    def __init__(self):
        self.workflows: Dict[str, CVJobWorkflow] = {}

    def create_workflow(self, job_id: str) -> CVJobWorkflow:
        """Create and track a new workflow"""
        workflow = CVJobWorkflow(job_id=job_id)
        self.workflows[job_id] = workflow
        return workflow

    def get_workflow(self, job_id: str) -> Optional[CVJobWorkflow]:
        """Get workflow by job_id"""
        return self.workflows.get(job_id)

    def update_workflow_state(
        self,
        job_id: str,
        new_state: JobState,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update workflow state.

        Args:
            job_id: Job identifier
            new_state: Target state
            error_message: Optional error message if transitioning to failed
            metadata: Optional metadata to store

        Returns:
            True if transition successful, False otherwise
        """
        workflow = self.get_workflow(job_id)
        if not workflow:
            return False

        # Validate transition
        if not workflow.can_transition_to(new_state):
            return False

        # Execute transition
        if new_state == JobState.PARSING:
            workflow.start_parsing()
        elif new_state == JobState.EVALUATING:
            workflow.complete_parsing()
        elif new_state == JobState.GENERATING_REPORT:
            workflow.complete_evaluation()
        elif new_state == JobState.COMPLETED:
            workflow.complete_report()
        elif new_state == JobState.FAILED:
            workflow.mark_failed()
            workflow.error_message = error_message

        # Update metadata
        if metadata:
            workflow.metadata.update(metadata)

        return True

    def remove_workflow(self, job_id: str):
        """Remove workflow from tracking"""
        if job_id in self.workflows:
            del self.workflows[job_id]
