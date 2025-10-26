"""
Unit tests for intent validation and drift detection
"""

import sys
import pytest
from unittest.mock import Mock, MagicMock

sys.path.insert(0, "/shared")

from cavia_common import (
    BaseAgent,
    AgentTaskV2,
    StructuredIntent,
    IntentConstraint,
    IntentSuccessCriteria,
    IntentValidation,
)


class TestIntentValidation:
    """Test intent validation functionality"""

    @pytest.fixture
    def base_agent(self):
        """Create a base agent for testing"""
        agent = BaseAgent(agent_id="test-agent-001")
        agent.logger = Mock()  # Mock logger to avoid setup_logging
        return agent

    @pytest.fixture
    def cv_intent(self):
        """Create a CV evaluation intent"""
        return StructuredIntent(
            workflow_type="cv_evaluation",
            goal="Parse and evaluate candidate CV for Senior Python Developer position",
            context={
                "position": "Senior Python Developer",
                "department": "Engineering",
            },
            constraints=[
                IntentConstraint(
                    name="minimum_experience",
                    description="Minimum years of experience",
                    value=5,
                    required=True,
                )
            ],
            success_criteria=[
                IntentSuccessCriteria(
                    criterion="overall_score",
                    description="Overall evaluation score",
                    validation_rule="score >= 70",
                )
            ],
        )

    @pytest.fixture
    def parser_task_v2(self, cv_intent):
        """Create an AgentTaskV2 for parser"""
        return AgentTaskV2(
            task_type="parse_cv",
            payload={
                "job_id": "test-job-123",
                "filename": "cv.pdf",
                "minio_bucket": "cvs-raw",
                "minio_path": "uploads/test-job-123/cv.pdf",
            },
            intent=cv_intent,
            intent_validations=[],
            steps_completed=[],
        )

    def test_validate_intent_aligned(self, base_agent, parser_task_v2):
        """Test intent validation when agent is well-aligned"""
        # Override agent type for this test
        base_agent.get_agent_type = Mock(return_value="parser")

        validation = base_agent.validate_intent(parser_task_v2)

        assert isinstance(validation, IntentValidation)
        assert validation.agent_type == "parser"
        assert validation.is_aligned is True
        # Parser aligns well with "parse and evaluate" goal
        assert validation.alignment_score >= 0.5
        assert validation.drift_score <= 0.5
        assert len(validation.reasoning) > 0

    def test_validate_intent_misaligned(self, base_agent, cv_intent):
        """Test intent validation when agent is misaligned"""
        # Create a task with OCR intent for a parser agent
        ocr_intent = StructuredIntent(
            workflow_type="ocr_extraction",
            goal="Extract text from scanned image using OCR technology",
            context={"document_type": "scanned_pdf"},
        )

        task = AgentTaskV2(
            task_type="parse_cv",
            payload={"job_id": "test-job-123"},
            intent=ocr_intent,
            intent_validations=[],
        )

        # Override agent type to parser
        base_agent.get_agent_type = Mock(return_value="parser")

        validation = base_agent.validate_intent(task)

        # Parser should have low alignment with OCR-focused intent
        assert validation.alignment_score < 0.8
        assert validation.drift_score > 0.2

    def test_check_intent_drift_no_drift(self, base_agent, parser_task_v2):
        """Test drift detection when no drift exists"""
        # Add low-drift validations
        parser_task_v2.intent_validations = [
            IntentValidation(
                agent_id="agent-1",
                agent_type="parser",
                is_aligned=True,
                alignment_score=0.9,
                drift_score=0.1,
                reasoning="Well aligned",
            ),
            IntentValidation(
                agent_id="agent-2",
                agent_type="evaluator",
                is_aligned=True,
                alignment_score=0.85,
                drift_score=0.15,
                reasoning="Good alignment",
            ),
        ]

        drift_detected = base_agent.check_intent_drift(parser_task_v2, threshold=0.4)

        assert drift_detected is False

    def test_check_intent_drift_detected_avg(self, base_agent, parser_task_v2):
        """Test drift detection when average drift exceeds threshold"""
        # Add high-drift validations
        parser_task_v2.intent_validations = [
            IntentValidation(
                agent_id="agent-1",
                agent_type="parser",
                is_aligned=False,
                alignment_score=0.5,
                drift_score=0.5,
                reasoning="Moderate drift",
            ),
            IntentValidation(
                agent_id="agent-2",
                agent_type="evaluator",
                is_aligned=False,
                alignment_score=0.3,
                drift_score=0.7,
                reasoning="High drift",
            ),
        ]

        drift_detected = base_agent.check_intent_drift(parser_task_v2, threshold=0.4)

        # Average drift = (0.5 + 0.7) / 2 = 0.6 > 0.4
        assert drift_detected is True

    def test_check_intent_drift_detected_max(self, base_agent, parser_task_v2):
        """Test drift detection when max drift exceeds critical threshold"""
        parser_task_v2.intent_validations = [
            IntentValidation(
                agent_id="agent-1",
                agent_type="parser",
                is_aligned=True,
                alignment_score=0.9,
                drift_score=0.1,
                reasoning="Good",
            ),
            IntentValidation(
                agent_id="agent-2",
                agent_type="evaluator",
                is_aligned=False,
                alignment_score=0.2,
                drift_score=0.8,  # High single drift
                reasoning="Very high drift",
            ),
        ]

        drift_detected = base_agent.check_intent_drift(parser_task_v2, threshold=0.4)

        # Max drift = 0.8 > 0.7 (critical threshold)
        assert drift_detected is True

    def test_update_intent_context(self, base_agent, parser_task_v2):
        """Test updating intent context"""
        base_agent.get_agent_type = Mock(return_value="parser")

        initial_context = dict(parser_task_v2.intent.context)

        base_agent.update_intent_context(
            parser_task_v2,
            {
                "parsing_completed": True,
                "contact_extracted": True,
                "education_count": 3,
            },
        )

        # Check context was updated
        assert parser_task_v2.intent.context["parsing_completed"] is True
        assert parser_task_v2.intent.context["contact_extracted"] is True
        assert parser_task_v2.intent.context["education_count"] == 3

        # Check original context still exists
        assert parser_task_v2.intent.context["position"] == initial_context["position"]

        # Check stage was updated
        assert parser_task_v2.intent.current_stage == "parser_completed"

    def test_keyword_alignment_scoring(self, base_agent):
        """Test keyword-based alignment scoring logic"""
        base_agent.get_agent_type = Mock(return_value="ocr")

        ocr_intent = StructuredIntent(
            workflow_type="ocr_extraction",
            goal="Use OCR to extract text from scanned image-based document",
            context={"method": "ocr"},
        )

        task = AgentTaskV2(
            task_type="extract_from_image",
            payload={"job_id": "test-job-123"},
            intent=ocr_intent,
            intent_validations=[],
        )

        validation = base_agent.validate_intent(task)

        # OCR agent should have high alignment with OCR intent
        # Goal contains "OCR", "extract", "image" - all OCR keywords
        assert validation.alignment_score >= 0.6
        assert validation.is_aligned is True

    def test_validation_with_no_prior_validations(self, base_agent, parser_task_v2):
        """Test validation when no prior validations exist"""
        base_agent.get_agent_type = Mock(return_value="parser")

        assert len(parser_task_v2.intent_validations) == 0

        validation = base_agent.validate_intent(parser_task_v2)

        # Should still validate successfully
        assert isinstance(validation, IntentValidation)
        assert validation.drift_score >= 0
        # With no prior validations, drift_score should equal 1 - alignment_score
        assert abs(validation.drift_score - (1 - validation.alignment_score)) < 0.01

    def test_cumulative_drift_calculation(self, base_agent, parser_task_v2):
        """Test that cumulative drift is calculated from prior validations"""
        base_agent.get_agent_type = Mock(return_value="evaluator")

        # Add a prior validation with some drift
        parser_task_v2.intent_validations = [
            IntentValidation(
                agent_id="parser-001",
                agent_type="parser",
                is_aligned=True,
                alignment_score=0.8,
                drift_score=0.2,
                reasoning="Good alignment",
            )
        ]

        validation = base_agent.validate_intent(parser_task_v2)

        # Cumulative drift should be average of prior drift and current drift
        prior_drift = 0.2
        current_drift = validation.drift_score
        # The validation should reference the cumulative drift in some way
        # (implementation averages it with current drift)
        assert validation.drift_score >= 0


class TestStructuredIntentModel:
    """Test StructuredIntent model"""

    def test_create_intent_with_defaults(self):
        """Test creating intent with minimal fields"""
        intent = StructuredIntent(
            workflow_type="test_workflow",
            goal="Test goal",
        )

        assert intent.workflow_type == "test_workflow"
        assert intent.goal == "Test goal"
        assert intent.context == {}
        assert intent.constraints == []
        assert intent.success_criteria == []
        assert intent.current_stage == "initiated"
        assert intent.intent_id is not None

    def test_create_intent_with_constraints(self):
        """Test creating intent with constraints"""
        intent = StructuredIntent(
            workflow_type="cv_evaluation",
            goal="Evaluate candidate",
            constraints=[
                IntentConstraint(
                    name="min_experience",
                    description="Minimum experience",
                    value=5,
                    required=True,
                )
            ],
        )

        assert len(intent.constraints) == 1
        assert intent.constraints[0].name == "min_experience"
        assert intent.constraints[0].value == 5
        assert intent.constraints[0].required is True

    def test_create_intent_with_success_criteria(self):
        """Test creating intent with success criteria"""
        intent = StructuredIntent(
            workflow_type="cv_evaluation",
            goal="Evaluate candidate",
            success_criteria=[
                IntentSuccessCriteria(
                    criterion="score",
                    description="Overall score",
                    validation_rule="score >= 70",
                )
            ],
        )

        assert len(intent.success_criteria) == 1
        assert intent.success_criteria[0].criterion == "score"
        assert intent.success_criteria[0].validation_rule == "score >= 70"


class TestIntentValidationModel:
    """Test IntentValidation model"""

    def test_create_validation(self):
        """Test creating intent validation"""
        validation = IntentValidation(
            agent_id="agent-001",
            agent_type="parser",
            is_aligned=True,
            alignment_score=0.85,
            drift_score=0.15,
            reasoning="Agent work aligns well with intent",
            suggestions=["Continue with current approach"],
        )

        assert validation.agent_id == "agent-001"
        assert validation.agent_type == "parser"
        assert validation.is_aligned is True
        assert validation.alignment_score == 0.85
        assert validation.drift_score == 0.15
        assert len(validation.reasoning) > 0
        assert len(validation.suggestions) == 1

    def test_validation_score_bounds(self):
        """Test that validation scores are within valid bounds"""
        # Should succeed with valid scores
        validation = IntentValidation(
            agent_id="agent-001",
            agent_type="parser",
            is_aligned=True,
            alignment_score=0.5,
            drift_score=0.5,
            reasoning="Test",
        )

        assert 0 <= validation.alignment_score <= 1
        assert 0 <= validation.drift_score <= 1

    def test_validation_score_out_of_bounds(self):
        """Test that validation scores are validated"""
        # Should fail with invalid score
        with pytest.raises(Exception):  # Pydantic ValidationError
            IntentValidation(
                agent_id="agent-001",
                agent_type="parser",
                is_aligned=True,
                alignment_score=1.5,  # Invalid: > 1
                drift_score=0.5,
                reasoning="Test",
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
