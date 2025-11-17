"""Workflow management API routes.

This module provides API endpoints for managing workflows.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks

from ..models import (
    APIResponse,
    ErrorResponse,
    WorkflowConfig,
    WorkflowStatus,
    CreateExecutionRequest,
    CreateExecutionResponse,
    GetExecutionResponse,
    ListExecutionsResponse,
    ExecutionResult,
    ValidateConfigRequest,
    ValidateConfigResponse,
)
from ...core.config import ConfigManager
from ...core.workflow import WorkflowEngine
from ...workflows.templates import get_template, list_templates, get_template_info
from ...utils.validation import validate_workflow_config

router = APIRouter()


@router.get(
    "/workflows",
    response_model=APIResponse,
    summary="List Workflows",
    description="Get a list of all configured workflows"
)
async def list_workflows(
    include_status: bool = Query(False, description="Include status information for each workflow")
) -> APIResponse:
    """List all configured workflows."""
    try:
        config_manager = ConfigManager()
        platform_config = config_manager.get_platform_config()

        workflows_data = []
        for workflow_config in platform_config.workflows:
            workflow_data = {
                "name": workflow_config.name,
                "description": workflow_config.description,
                "type": workflow_config.type,
                "steps": len(workflow_config.steps),
                "agents": workflow_config.agents,
                "timeout": workflow_config.timeout,
            }

            if include_status:
                # Get workflow status (simplified)
                workflow_data["status"] = "configured"
                workflow_data["last_execution"] = None
                workflow_data["success_rate"] = None

            workflows_data.append(workflow_data)

        return APIResponse(
            success=True,
            data=workflows_data,
            message=f"Found {len(workflows_data)} workflows"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list workflows: {str(e)}"
        )


@router.get(
    "/workflows/{workflow_name}",
    response_model=APIResponse,
    summary="Get Workflow",
    description="Get detailed information about a specific workflow"
)
async def get_workflow(workflow_name: str) -> APIResponse:
    """Get information about a specific workflow."""
    try:
        config_manager = ConfigManager()
        platform_config = config_manager.get_platform_config()

        # Find workflow
        workflow_config = None
        for workflow in platform_config.workflows:
            if workflow.name == workflow_name:
                workflow_config = workflow
                break

        if not workflow_config:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_name}' not found")

        workflow_data = {
            "name": workflow_config.name,
            "description": workflow_config.description,
            "type": workflow_config.type,
            "steps": [step.dict() for step in workflow_config.steps],
            "agents": workflow_config.agents,
            "timeout": workflow_config.timeout,
            "metadata": workflow_config.metadata,
        }

        return APIResponse(
            success=True,
            data=workflow_data,
            message=f"Workflow '{workflow_name}' found"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get workflow: {str(e)}"
        )


@router.post(
    "/workflows",
    response_model=APIResponse,
    summary="Create Workflow",
    description="Create a new workflow configuration"
)
async def create_workflow(workflow_config: WorkflowConfig) -> APIResponse:
    """Create a new workflow."""
    try:
        config_manager = ConfigManager()
        platform_config = config_manager.get_platform_config()

        # Check if workflow already exists
        existing_names = [wf.name for wf in platform_config.workflows]
        if workflow_config.name in existing_names:
            raise HTTPException(
                status_code=409,
                detail=f"Workflow '{workflow_config.name}' already exists"
            )

        # Validate workflow configuration
        validation_result = validate_workflow_config(workflow_config.dict())
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid workflow configuration: {', '.join(validation_result.errors)}"
            )

        # Add workflow to configuration
        platform_config.workflows.append(workflow_config)

        # Save configuration
        config_manager.save_config(platform_config)

        return APIResponse(
            success=True,
            data=workflow_config.dict(),
            message=f"Workflow '{workflow_config.name}' created successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create workflow: {str(e)}"
        )


@router.put(
    "/workflows/{workflow_name}",
    response_model=APIResponse,
    summary="Update Workflow",
    description="Update an existing workflow configuration"
)
async def update_workflow(workflow_name: str, workflow_config: WorkflowConfig) -> APIResponse:
    """Update an existing workflow."""
    try:
        config_manager = ConfigManager()
        platform_config = config_manager.get_platform_config()

        # Find and update workflow
        workflow_found = False
        for i, workflow in enumerate(platform_config.workflows):
            if workflow.name == workflow_name:
                # Validate new configuration
                validation_result = validate_workflow_config(workflow_config.dict())
                if not validation_result.is_valid:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid workflow configuration: {', '.join(validation_result.errors)}"
                    )

                platform_config.workflows[i] = workflow_config
                workflow_found = True
                break

        if not workflow_found:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_name}' not found")

        # Save configuration
        config_manager.save_config(platform_config)

        return APIResponse(
            success=True,
            data=workflow_config.dict(),
            message=f"Workflow '{workflow_name}' updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update workflow: {str(e)}"
        )


@router.delete(
    "/workflows/{workflow_name}",
    response_model=APIResponse,
    summary="Delete Workflow",
    description="Delete a workflow configuration"
)
async def delete_workflow(workflow_name: str) -> APIResponse:
    """Delete a workflow."""
    try:
        config_manager = ConfigManager()
        platform_config = config_manager.get_platform_config()

        # Find and remove workflow
        original_count = len(platform_config.workflows)
        platform_config.workflows = [wf for wf in platform_config.workflows if wf.name != workflow_name]

        if len(platform_config.workflows) == original_count:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_name}' not found")

        # Save configuration
        config_manager.save_config(platform_config)

        return APIResponse(
            success=True,
            message=f"Workflow '{workflow_name}' deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete workflow: {str(e)}"
        )


@router.get(
    "/workflows/templates",
    response_model=APIResponse,
    summary="List Templates",
    description="Get a list of available workflow templates"
)
async def list_workflow_templates() -> APIResponse:
    """List available workflow templates."""
    try:
        templates = list_templates()
        templates_info = []

        for template_name in templates:
            template_info = get_template_info(template_name)
            templates_info.append(template_info)

        return APIResponse(
            success=True,
            data=templates_info,
            message=f"Found {len(templates_info)} workflow templates"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list workflow templates: {str(e)}"
        )


@router.post(
    "/workflows/templates/{template_name}",
    response_model=APIResponse,
    summary="Create from Template",
    description="Create a new workflow from a template"
)
async def create_from_template(
    template_name: str,
    workflow_name: str = Query(..., description="Name for the new workflow"),
    description: Optional[str] = Query(None, description="Workflow description")
) -> APIResponse:
    """Create a workflow from a template."""
    try:
        # Get template
        template = get_template(template_name)

        config_manager = ConfigManager()
        platform_config = config_manager.get_platform_config()

        # Check if workflow already exists
        existing_names = [wf.name for wf in platform_config.workflows]
        if workflow_name in existing_names:
            raise HTTPException(
                status_code=409,
                detail=f"Workflow '{workflow_name}' already exists"
            )

        # Create workflow from template
        template_config = template.get_template_config()
        template_config["name"] = workflow_name

        if description:
            template_config["description"] = description

        # Convert to WorkflowConfig
        from ...api.models import WorkflowStep

        steps = []
        for step_data in template_config["steps"]:
            step = WorkflowStep(**step_data)
            steps.append(step)

        workflow_config = WorkflowConfig(
            name=template_config["name"],
            description=template_config.get("description"),
            type=template_config["type"],
            steps=steps,
            agents=template_config["agents"],
            timeout=template_config.get("timeout"),
        )

        # Add to platform config
        platform_config.workflows.append(workflow_config)

        # Save configuration
        config_manager.save_config(platform_config)

        return APIResponse(
            success=True,
            data=workflow_config.dict(),
            message=f"Workflow '{workflow_name}' created from template '{template_name}'"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create workflow from template: {str(e)}"
        )


@router.post(
    "/workflows/validate",
    response_model=ValidateConfigResponse,
    summary="Validate Workflow Config",
    description="Validate a workflow configuration"
)
async def validate_workflow(request: ValidateConfigRequest) -> ValidateConfigResponse:
    """Validate workflow configuration."""
    try:
        validation_result = validate_workflow_config(request.config)

        return ValidateConfigResponse(
            errors=validation_result.errors,
            warnings=validation_result.warnings,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate workflow configuration: {str(e)}"
        )