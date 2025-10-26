"""
Unit tests for workflow templates
"""

import sys
import pytest

sys.path.insert(0, "/shared")

from cavia_common import (
    WorkflowTemplate,
    get_workflow_template,
    list_workflow_templates,
    get_workflows_by_category,
    WORKFLOW_TEMPLATES,
)


class TestWorkflowTemplates:
    """Test workflow template functionality"""

    def test_list_workflow_templates(self):
        """Test listing all workflow templates"""
        workflows = list_workflow_templates()

        assert len(workflows) > 0
        assert all(isinstance(w, WorkflowTemplate) for w in workflows)

        # Check that expected workflows exist
        workflow_ids = [w.workflow_id for w in workflows]
        assert "cv_evaluation" in workflow_ids
        assert "cv_evaluation_scanned" in workflow_ids
        assert "expense_evaluation" in workflow_ids
        assert "invoice_processing" in workflow_ids

    def test_get_workflow_template_exists(self):
        """Test getting a specific workflow template"""
        workflow = get_workflow_template("cv_evaluation")

        assert workflow is not None
        assert workflow.workflow_id == "cv_evaluation"
        assert workflow.name == "CV Evaluation"
        assert "pdf" in workflow.document_types
        assert workflow.category == "hr"
        assert workflow.icon in ["cv", "document", "file-text"]

    def test_get_workflow_template_not_exists(self):
        """Test getting a non-existent workflow"""
        workflow = get_workflow_template("non_existent_workflow")

        assert workflow is None

    def test_get_workflows_by_category(self):
        """Test filtering workflows by category"""
        hr_workflows = get_workflows_by_category("hr")

        assert len(hr_workflows) > 0
        assert all(w.category == "hr" for w in hr_workflows)

        # Should include CV workflows
        workflow_ids = [w.workflow_id for w in hr_workflows]
        assert "cv_evaluation" in workflow_ids

    def test_get_workflows_by_category_empty(self):
        """Test filtering by non-existent category"""
        workflows = get_workflows_by_category("non_existent_category")

        assert workflows == []

    def test_cv_evaluation_workflow_structure(self):
        """Test CV evaluation workflow has correct structure"""
        workflow = get_workflow_template("cv_evaluation")

        assert workflow is not None

        # Check intent template structure
        template = workflow.intent_template
        assert "workflow_type" in template
        assert "goal" in template
        assert "context" in template
        assert "constraints" in template
        assert "success_criteria" in template

        # Check workflow type matches
        assert template["workflow_type"] == "cv_evaluation"

        # Check goal has placeholders
        assert "{{" in template["goal"]
        assert "}}" in template["goal"]

        # Check constraints exist
        assert len(template["constraints"]) > 0
        for constraint in template["constraints"]:
            assert "name" in constraint
            assert "description" in constraint
            assert "value" in constraint

        # Check success criteria exist
        assert len(template["success_criteria"]) > 0
        for criterion in template["success_criteria"]:
            assert "criterion" in criterion
            assert "description" in criterion

    def test_scanned_cv_workflow(self):
        """Test scanned CV workflow configuration"""
        workflow = get_workflow_template("cv_evaluation_scanned")

        assert workflow is not None
        assert workflow.workflow_id == "cv_evaluation_scanned"
        assert workflow.category == "hr"

        # Should support image formats
        assert any(fmt in workflow.document_types for fmt in ["png", "jpg", "jpeg", "pdf"])

        # Should have OCR-related first agent query
        assert "ocr" in workflow.first_agent_query.lower() or "scan" in workflow.first_agent_query.lower()

    def test_expense_evaluation_workflow(self):
        """Test expense evaluation workflow"""
        workflow = get_workflow_template("expense_evaluation")

        assert workflow is not None
        assert workflow.workflow_id == "expense_evaluation"
        assert workflow.category == "finance"

        # Check template has expense-specific fields
        template = workflow.intent_template
        assert template["workflow_type"] == "expense_evaluation"

        # Should have expense-related constraints
        constraint_names = [c["name"] for c in template["constraints"]]
        assert any("amount" in name.lower() or "category" in name.lower() for name in constraint_names)

    def test_invoice_processing_workflow(self):
        """Test invoice processing workflow"""
        workflow = get_workflow_template("invoice_processing")

        assert workflow is not None
        assert workflow.workflow_id == "invoice_processing"
        assert workflow.category == "finance"

        # Should support PDF
        assert "pdf" in workflow.document_types

        template = workflow.intent_template
        assert template["workflow_type"] == "invoice_processing"

    def test_workflow_example_intents(self):
        """Test that workflows have example intents"""
        workflow = get_workflow_template("cv_evaluation")

        assert workflow is not None
        assert len(workflow.example_intents) > 0
        assert all(isinstance(example, str) for example in workflow.example_intents)
        assert all(len(example) > 0 for example in workflow.example_intents)

    def test_workflow_template_uniqueness(self):
        """Test that workflow IDs are unique"""
        workflows = list_workflow_templates()
        workflow_ids = [w.workflow_id for w in workflows]

        assert len(workflow_ids) == len(set(workflow_ids)), "Duplicate workflow IDs found"

    def test_all_workflows_have_required_fields(self):
        """Test that all workflows have required fields"""
        workflows = list_workflow_templates()

        for workflow in workflows:
            # Required fields
            assert workflow.workflow_id
            assert workflow.name
            assert workflow.description
            assert len(workflow.document_types) > 0
            assert workflow.category
            assert workflow.icon
            assert workflow.first_agent_query

            # Intent template required fields
            template = workflow.intent_template
            assert "workflow_type" in template
            assert "goal" in template
            assert isinstance(template.get("context", {}), dict)
            assert isinstance(template.get("constraints", []), list)
            assert isinstance(template.get("success_criteria", []), list)

    def test_constraint_validation_rules(self):
        """Test that constraints have proper structure"""
        workflows = list_workflow_templates()

        for workflow in workflows:
            for constraint in workflow.intent_template.get("constraints", []):
                assert "name" in constraint
                assert "description" in constraint
                assert "value" in constraint
                # Required field should be boolean or default to True
                assert isinstance(constraint.get("required", True), bool)

    def test_success_criteria_structure(self):
        """Test that success criteria have proper structure"""
        workflows = list_workflow_templates()

        for workflow in workflows:
            for criterion in workflow.intent_template.get("success_criteria", []):
                assert "criterion" in criterion
                assert "description" in criterion
                # validation_rule is optional but should be string if present
                if "validation_rule" in criterion:
                    assert isinstance(criterion["validation_rule"], str)


class TestWorkflowTemplateModel:
    """Test WorkflowTemplate model"""

    def test_create_workflow_template(self):
        """Test creating a workflow template"""
        workflow = WorkflowTemplate(
            workflow_id="test_workflow",
            name="Test Workflow",
            description="A test workflow",
            document_types=["pdf"],
            category="test",
            icon="test-icon",
            first_agent_query="test query",
            intent_template={
                "workflow_type": "test_workflow",
                "goal": "Test goal",
                "context": {},
                "constraints": [],
                "success_criteria": [],
            },
            example_intents=["Example 1", "Example 2"],
        )

        assert workflow.workflow_id == "test_workflow"
        assert workflow.name == "Test Workflow"
        assert workflow.category == "test"
        assert len(workflow.example_intents) == 2

    def test_workflow_template_defaults(self):
        """Test workflow template default values"""
        workflow = WorkflowTemplate(
            workflow_id="minimal_workflow",
            name="Minimal",
            description="Minimal workflow",
            document_types=["pdf"],
            category="test",
            icon="icon",
            first_agent_query="query",
            intent_template={
                "workflow_type": "minimal",
                "goal": "Goal",
            },
        )

        # example_intents should default to empty list
        assert workflow.example_intents == []


class TestWorkflowIntegration:
    """Integration tests for workflow system"""

    def test_workflow_to_intent_creation(self):
        """Test creating a StructuredIntent from workflow template"""
        from cavia_common import StructuredIntent

        workflow = get_workflow_template("cv_evaluation")
        template = workflow.intent_template

        # Simulate parameter filling
        goal = template["goal"]
        goal = goal.replace("{{position}}", "Senior Python Developer")
        goal = goal.replace("{{department}}", "Engineering")

        # Create intent
        intent = StructuredIntent(
            workflow_type=template["workflow_type"],
            goal=goal,
            context={
                "position": "Senior Python Developer",
                "department": "Engineering",
            },
            constraints=template["constraints"],
            success_criteria=template["success_criteria"],
        )

        assert intent.workflow_type == "cv_evaluation"
        assert "Senior Python Developer" in intent.goal
        assert intent.context["position"] == "Senior Python Developer"
        assert len(intent.constraints) > 0
        assert len(intent.success_criteria) > 0

    def test_all_categories_valid(self):
        """Test that all workflow categories are valid"""
        valid_categories = {"hr", "finance", "legal", "operations", "general"}
        workflows = list_workflow_templates()

        for workflow in workflows:
            assert workflow.category in valid_categories, f"Invalid category: {workflow.category}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
