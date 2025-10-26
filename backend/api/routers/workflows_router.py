"""
Workflows Router - API endpoints for workflow templates and intent management
"""

import sys
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

sys.path.insert(0, "/shared")

from cavia_common import (
    get_logger,
    list_workflow_templates,
    get_workflow_template,
    get_workflows_by_category,
    WorkflowTemplate,
    StructuredIntent,
)

logger = get_logger(__name__)
router = APIRouter()


class WorkflowResponse(BaseModel):
    """Response model for workflow template"""
    workflow_id: str
    name: str
    description: str
    document_types: List[str]
    intent_template: Dict[str, Any]
    example_intents: List[str]
    icon: str
    category: str


class IntentCreateRequest(BaseModel):
    """Request model for creating an intent from a template"""
    workflow_id: str
    parameters: Dict[str, Any]  # Values to fill template placeholders


@router.get("/workflows", response_model=List[WorkflowResponse])
async def list_workflows():
    """
    List all available workflow templates.

    Returns:
        List of workflow templates with their configurations
    """
    try:
        workflows = list_workflow_templates()

        return [
            WorkflowResponse(
                workflow_id=wf.workflow_id,
                name=wf.name,
                description=wf.description,
                document_types=wf.document_types,
                intent_template=wf.intent_template,
                example_intents=wf.example_intents,
                icon=wf.icon,
                category=wf.category
            )
            for wf in workflows
        ]
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve workflows: {str(e)}"
        )


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str):
    """
    Get a specific workflow template by ID.

    Args:
        workflow_id: The workflow template ID

    Returns:
        Workflow template details
    """
    try:
        workflow = get_workflow_template(workflow_id)

        if not workflow:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow '{workflow_id}' not found"
            )

        return WorkflowResponse(
            workflow_id=workflow.workflow_id,
            name=workflow.name,
            description=workflow.description,
            document_types=workflow.document_types,
            intent_template=workflow.intent_template,
            example_intents=workflow.example_intents,
            icon=workflow.icon,
            category=workflow.category
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve workflow: {str(e)}"
        )


@router.get("/workflows/category/{category}", response_model=List[WorkflowResponse])
async def get_workflows_by_category_route(category: str):
    """
    Get workflows filtered by category.

    Args:
        category: Category to filter by (e.g., 'hr', 'finance')

    Returns:
        List of workflows in the specified category
    """
    try:
        workflows = get_workflows_by_category(category)

        return [
            WorkflowResponse(
                workflow_id=wf.workflow_id,
                name=wf.name,
                description=wf.description,
                document_types=wf.document_types,
                intent_template=wf.intent_template,
                example_intents=wf.example_intents,
                icon=wf.icon,
                category=wf.category
            )
            for wf in workflows
        ]
    except Exception as e:
        logger.error(f"Failed to get workflows for category {category}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve workflows: {str(e)}"
        )


@router.post("/workflows/{workflow_id}/intent", response_model=Dict[str, Any])
async def create_intent_from_template(workflow_id: str, request: IntentCreateRequest):
    """
    Create a StructuredIntent from a workflow template with user parameters.

    Args:
        workflow_id: The workflow template ID
        request: Parameters to fill template placeholders

    Returns:
        StructuredIntent ready for use in document upload
    """
    try:
        workflow = get_workflow_template(workflow_id)

        if not workflow:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow '{workflow_id}' not found"
            )

        # Get template
        template = workflow.intent_template

        # Fill in user parameters
        # Replace {{placeholders}} in goal
        goal = template["goal"]
        context = template.get("context", {}).copy()

        for key, value in request.parameters.items():
            placeholder = f"{{{{{key}}}}}"
            goal = goal.replace(placeholder, str(value))
            if key in context:
                context[key] = value

        # Create StructuredIntent
        intent_dict = {
            "workflow_type": template["workflow_type"],
            "goal": goal,
            "context": context,
            "constraints": template.get("constraints", []),
            "success_criteria": template.get("success_criteria", [])
        }

        # Validate with Pydantic
        intent = StructuredIntent(**intent_dict)

        logger.info(
            f"Created intent from workflow {workflow_id}",
            intent_id=intent.intent_id,
            goal=intent.goal
        )

        return intent.dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create intent from workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create intent: {str(e)}"
        )


@router.get("/workflows/categories", response_model=List[str])
async def list_workflow_categories():
    """
    List all available workflow categories.

    Returns:
        List of unique category names
    """
    try:
        workflows = list_workflow_templates()
        categories = list(set(wf.category for wf in workflows))
        categories.sort()
        return categories
    except Exception as e:
        logger.error(f"Failed to list categories: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve categories: {str(e)}"
        )
