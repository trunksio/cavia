"""
Base Agent class for all Agentic Units
"""

import os
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from threading import Thread
import signal
import sys

from sentence_transformers import SentenceTransformer

from rq import Queue, Worker

from .config import get_settings
from .logging import get_logger, setup_logging
from .models import AgentRegistration, AgentStatus, AgentTask, AgentTaskResult
from .database import get_db_manager
from .redis_client import get_redis_connection


class BaseAgent(ABC):
    """
    Base class for all Agentic Units in the AOA system.

    Each agent must implement:
    - get_agent_info(): Return agent metadata
    - process_task(task): Process a task and return result
    """

    def __init__(self, agent_id: Optional[str] = None):
        # Setup logging first
        setup_logging()
        self.logger = get_logger(self.__class__.__name__)

        # Configuration
        self.settings = get_settings()
        self.agent_id = agent_id or f"{self.get_agent_type()}-{uuid.uuid4().hex[:8]}"

        # Clients
        self.db = get_db_manager()
        self.redis_conn = get_redis_connection()  # Direct Redis connection for RQ

        # State
        self.status = AgentStatus.STARTING
        self.heartbeat_thread: Optional[Thread] = None
        self.running = False

        # Embedding model for semantic descriptions (lazy-loaded)
        self._embedding_model: Optional[SentenceTransformer] = None

        self.logger.info("Agent initialized", agent_id=self.agent_id)

    def _get_embedding_model(self) -> SentenceTransformer:
        """
        Lazy-load the sentence transformers embedding model.

        Only loads the model when actually needed (registration or discovery),
        preventing issues in RQ worker forked processes that don't use it.
        """
        if self._embedding_model is None:
            self.logger.info("Loading sentence transformers model", model=self.settings.embedding_model)
            self._embedding_model = SentenceTransformer(self.settings.embedding_model)
        return self._embedding_model

    @abstractmethod
    def get_agent_type(self) -> str:
        """Return the agent type (e.g., 'parser', 'evaluator')"""
        pass

    @abstractmethod
    def get_agent_info(self) -> Dict[str, Any]:
        """
        Return agent metadata for registration.

        Returns:
            dict with keys: name, description, capabilities
        """
        pass

    @abstractmethod
    def process_task(self, task: AgentTask) -> AgentTaskResult:
        """
        Process a task and return result.

        Args:
            task: AgentTask with task_id, task_type, and payload

        Returns:
            AgentTaskResult with status, result, or error
        """
        pass

    def register(self) -> bool:
        """Register this agent in the semantic registry"""
        try:
            info = self.get_agent_info()

            # Generate semantic embedding (lazy-loads model on first use)
            description = f"{info['name']}: {info['description']}"
            embedding = self._get_embedding_model().encode(description)

            # Create registration
            registration = AgentRegistration(
                agent_id=self.agent_id,
                agent_type=self.get_agent_type(),
                name=info["name"],
                description=info["description"],
                capabilities=info["capabilities"],
                queue_name=self.get_queue_name(),
                status=AgentStatus.ACTIVE,
            )

            # Register in database
            success = self.db.register_agent(
                agent_id=self.agent_id,
                agent_type=registration.agent_type,
                name=registration.name,
                description=registration.description,
                capabilities=registration.capabilities,
                queue_name=registration.queue_name,
                semantic_embedding=embedding,
            )

            if success:
                self.status = AgentStatus.ACTIVE
                self.logger.info("Agent registered successfully", agent_id=self.agent_id)
            else:
                self.logger.error("Agent registration failed", agent_id=self.agent_id)

            return success

        except Exception as e:
            self.logger.error("Registration error", agent_id=self.agent_id, error=str(e))
            self.status = AgentStatus.ERROR
            return False

    def get_queue_name(self) -> str:
        """Get the queue name for this agent type"""
        agent_type = self.get_agent_type()
        queue_mapping = {
            "parser": self.settings.queue_parsing,
            "evaluator": self.settings.queue_evaluation,
            "orchestrator": self.settings.queue_orchestration,
            "reporter": self.settings.queue_reporting,
        }
        return queue_mapping.get(agent_type, f"queue-{agent_type}")

    def start_heartbeat(self) -> None:
        """Start heartbeat thread"""
        def heartbeat_loop():
            while self.running:
                try:
                    self.db.update_heartbeat(self.agent_id)
                    self.logger.debug("Heartbeat sent", agent_id=self.agent_id)
                except Exception as e:
                    self.logger.error("Heartbeat error", error=str(e))

                time.sleep(self.settings.agent_heartbeat_interval)

        self.running = True
        self.heartbeat_thread = Thread(target=heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        self.logger.info("Heartbeat started", agent_id=self.agent_id)

    def stop_heartbeat(self) -> None:
        """Stop heartbeat thread"""
        self.running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
        self.logger.info("Heartbeat stopped", agent_id=self.agent_id)

    def start_worker(self) -> None:
        """Start RQ worker to process tasks"""
        try:
            # Register signal handlers
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)

            # Register agent
            if not self.register():
                raise Exception("Failed to register agent")

            # Start heartbeat
            self.start_heartbeat()

            # Register this agent instance for RQ job processing
            register_agent_instance(self)

            # Start RQ worker - use RQ directly
            queue_name = self.get_queue_name()
            self.logger.info("Starting worker", queue=queue_name, agent_id=self.agent_id)

            # Create queue and worker using RQ directly
            queue = Queue(queue_name, connection=self.redis_conn)
            worker = Worker([queue], connection=self.redis_conn, name=self.agent_id)

            # Work loop
            worker.work()

        except Exception as e:
            self.logger.error("Worker error", error=str(e))
            self.status = AgentStatus.ERROR
            raise
        finally:
            self.stop_heartbeat()
            self.status = AgentStatus.INACTIVE

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info("Shutdown signal received", signal=signum)
        self.stop_heartbeat()
        self.status = AgentStatus.STOPPING
        sys.exit(0)

    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.get_agent_type(),
            "status": self.status.value,
            "queue": self.get_queue_name(),
        }

    def discover_next_agent(self, capability_query: str) -> Optional[Dict[str, str]]:
        """
        Discover the next agent to handle a capability using semantic search.

        Args:
            capability_query: Natural language description of needed capability
                             (e.g., "evaluate CV against criteria")

        Returns:
            Dict with 'agent_type' and 'queue_name', or None if not found
        """
        try:
            # Generate embedding for the capability query (lazy-loads model on first use)
            query_embedding = self._get_embedding_model().encode(capability_query)

            # Search semantic registry for best match
            agent_info = self.db.search_agents_by_capability(
                query_embedding=query_embedding,
                limit=1
            )

            if agent_info:
                best_match = agent_info[0]
                self.logger.info(
                    "Discovered next agent",
                    capability=capability_query,
                    agent_type=best_match['agent_type'],
                    queue=best_match['queue_name']
                )
                return {
                    "agent_type": best_match['agent_type'],
                    "queue_name": best_match['queue_name']
                }
            else:
                self.logger.warning("No agent found for capability", capability=capability_query)
                return None

        except Exception as e:
            self.logger.error("Failed to discover next agent", capability=capability_query, error=str(e))
            return None

    def enqueue_to_next_agent(
        self,
        capability_query: str,
        task_type: str,
        payload: Dict[str, Any],
        intent: str,
        steps_completed: list[str]
    ) -> Optional[str]:
        """
        Discover and enqueue task to the next agent in the chain.

        Args:
            capability_query: What capability is needed next
            task_type: Type of task for the next agent
            payload: Task payload data
            intent: Original intent being fulfilled
            steps_completed: List of agent types that have already processed this

        Returns:
            RQ job ID if successful, None otherwise
        """
        try:
            import uuid
            from rq import Queue

            # Discover next agent
            next_agent = self.discover_next_agent(capability_query)
            if not next_agent:
                raise Exception(f"No agent found for capability: {capability_query}")

            # Update steps_completed with current agent type
            updated_steps = steps_completed + [self.get_agent_type()]

            # Create task
            task_dict = {
                "task_id": str(uuid.uuid4()),
                "task_type": task_type,
                "payload": payload,
                "intent": intent,
                "steps_completed": updated_steps,
            }

            # Enqueue to discovered agent's queue
            queue = Queue(next_agent['queue_name'], connection=self.redis_conn)
            job = queue.enqueue(
                "cavia_common.base_agent.process_agent_task",
                task_dict,
                job_timeout='15m',
                result_ttl=3600,
            )

            self.logger.info(
                "Enqueued to next agent",
                next_agent_type=next_agent['agent_type'],
                queue=next_agent['queue_name'],
                job_id=job.id,
                intent=intent
            )

            return job.id

        except Exception as e:
            self.logger.error("Failed to enqueue to next agent", error=str(e))
            return None


# Global agent registry for RQ workers
_agent_instance: Optional[BaseAgent] = None


def register_agent_instance(agent: BaseAgent) -> None:
    """Register the agent instance for this worker process"""
    global _agent_instance
    _agent_instance = agent


def process_agent_task(task_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    RQ job function that processes agent tasks.

    This is the entry point called by RQ workers. It delegates to the
    registered agent instance's process_task() method.

    Args:
        task_dict: Dictionary representation of AgentTask

    Returns:
        Dictionary representation of AgentTaskResult
    """
    global _agent_instance

    if _agent_instance is None:
        raise RuntimeError(
            "No agent instance registered. "
            "Agent must call register_agent_instance() before starting worker."
        )

    # Deserialize task
    task = AgentTask(**task_dict)

    # Process task using the agent instance
    result = _agent_instance.process_task(task)

    # Return result as dict
    return result.dict() if hasattr(result, 'dict') else result
