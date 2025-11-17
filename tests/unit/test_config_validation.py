"""Unit tests for configuration validation."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open

from src.core.config import (
    PlatformConfig,
    GlobalConfig,
    AgentConfigEntry,
    WorkflowConfigEntry,
    ObservabilityConfig,
    DeploymentConfig,
    ConfigManager,
    PlatformConfig,
)
from src.utils.validation import validate_config_file, ValidationResult, validate_config


class TestConfigValidation:
    """Test configuration validation functionality."""

    def test_platform_config_creation(self):
        """Test creating a valid platform configuration."""
        config = PlatformConfig(
            version="1.0.0",
            global_=GlobalConfig(
                workspace_dir="/tmp/workspace",
                log_level="INFO",
                max_concurrent_workflows=5,
                timeout_seconds=300,
            ),
            agents={
                "claude": AgentConfigEntry(
                    name="claude",
                    provider="anthropic",
                    model="claude-3-sonnet-20240229",
                    api_key="test-key",
                    max_tokens=4096,
                    temperature=0.7,
                    timeout_seconds=60,
                )
            },
            workflows={
                "test-workflow": WorkflowConfigEntry(
                    name="test-workflow",
                    type="simple",
                    description="Test workflow",
                    agents=["claude"],
                    steps=[
                        {
                            "name": "step1",
                            "agent": "claude",
                            "prompt_template": "Test prompt",
                            "output_key": "result"
                        }
                    ],
                )
            }
        )

        assert config.version == "1.0.0"
        assert config.global_.workspace_dir == "/tmp/workspace"
        assert len(config.agents) == 1
        assert len(config.workflows) == 1

    def test_config_manager_initialization(self):
        """Test ConfigManager initialization."""
        manager = ConfigManager()
        assert manager.config_file is not None

    def test_config_manager_load_config(self):
        """Test loading configuration from file."""
        config_data = {
            "version": "1.0.0",
            "global": {
                "workspace_dir": "/tmp/test",
                "log_level": "INFO",
                "max_concurrent_workflows": 5,
                "timeout_seconds": 300,
            },
            "agents": {},
            "workflows": {},
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(config_data, f)
            config_file = f.name

        try:
            manager = ConfigManager(config_file)
            config = manager.load_config()

            assert config.version == "1.0.0"
            assert config.global_.workspace_dir == "/tmp/test"
        finally:
            os.unlink(config_file)

    def test_config_validation_valid_config(self):
        """Test validation of a valid configuration."""
        config = {
            "version": "1.0.0",
            "global": {
                "workspace_dir": "/tmp/test",
                "log_level": "INFO",
                "max_concurrent_workflows": 5,
                "timeout_seconds": 300,
            },
            "agents": {
                "claude": {
                    "name": "claude",
                    "provider": "anthropic",
                    "model": "claude-3-sonnet-20240229",
                    "api_key": "test-key",
                    "max_tokens": 4096,
                    "temperature": 0.7,
                    "timeout_seconds": 60,
                    "enabled": True,
                }
            },
            "workflows": {
                "test-workflow": {
                    "name": "test-workflow",
                    "type": "simple",
                    "description": "Test workflow",
                    "agents": ["claude"],
                    "steps": [
                        {
                            "name": "step1",
                            "agent": "claude",
                            "prompt_template": "Test prompt",
                            "output_key": "result"
                        }
                    ],
                    "enabled": True,
                }
            }
        }

        result = validate_config_file(config)  # Direct call to validate config dict
        assert result.is_valid
        assert len(result.errors) == 0

    def test_config_validation_invalid_version(self):
        """Test validation with invalid version."""
        config = {
            "version": "invalid",
            "global": {
                "workspace_dir": "/tmp/test",
                "log_level": "INFO",
                "max_concurrent_workflows": 5,
                "timeout_seconds": 300,
            },
            "agents": {},
            "workflows": {},
        }

        result = validate_config(config)
        assert not result.is_valid
        assert len(result.errors) > 0
        assert "Required configuration key missing: version" in result.errors

    def test_config_validation_missing_required_fields(self):
        """Test validation with missing required fields."""
        config = {
            "version": "1.0.0",
            # Missing global section
            "agents": {},
            "workflows": {},
        }

        result = validate_config(config)
        assert not result.is_valid
        assert len(result.errors) > 0

    def test_config_validation_invalid_agent_config(self):
        """Test validation with invalid agent configuration."""
        config = {
            "version": "1.0.0",
            "global": {
                "workspace_dir": "/tmp/test",
                "log_level": "INFO",
                "max_concurrent_workflows": 5,
                "timeout_seconds": 300,
            },
            "agents": {
                "invalid-agent": {
                    "name": "invalid-agent",
                    # Missing required provider field
                    "model": "some-model",
                    "api_key": "test-key",
                }
            },
            "workflows": {},
        }

        result = validate_config(config)
        assert not result.is_valid
        assert len(result.errors) > 0

    def test_config_validation_invalid_workflow_config(self):
        """Test validation with invalid workflow configuration."""
        config = {
            "version": "1.0.0",
            "global": {
                "workspace_dir": "/tmp/test",
                "log_level": "INFO",
                "max_concurrent_workflows": 5,
                "timeout_seconds": 300,
            },
            "agents": {},
            "workflows": {
                "invalid-workflow": {
                    "name": "invalid-workflow",
                    # Missing required type field
                    "description": "Invalid workflow",
                    "steps": [],
                }
            },
        }

        result = validate_config(config)
        assert not result.is_valid
        assert len(result.errors) > 0

    def test_config_file_not_found(self):
        """Test validation when config file doesn't exist."""
        result = validate_config_file("/nonexistent/file.yaml")
        assert not result.is_valid
        assert len(result.errors) > 0
        assert "Configuration file not found" in result.errors[0]

    def test_config_file_invalid_format(self):
        """Test validation with invalid file format."""
        result = validate_config_file("/nonexistent/file.invalid")
        assert not result.is_valid
        assert len(result.errors) > 0
        assert "Unsupported configuration file format" in result.errors[0]

    def test_config_validation_with_json_file(self):
        """Test validation with JSON configuration file."""
        config_data = {
            "version": "1.0.0",
            "global": {
                "workspace_dir": "/tmp/test",
                "log_level": "INFO",
                "max_concurrent_workflows": 5,
                "timeout_seconds": 300,
            },
            "agents": {},
            "workflows": {},
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            import json
            json.dump(config_data, f)
            config_file = f.name

        try:
            result = validate_config_file(config_file)
            assert result.is_valid
        finally:
            os.unlink(config_file)

    def test_config_validation_empty_config(self):
        """Test validation with empty configuration."""
        config = {}

        result = validate_config(config)
        assert not result.is_valid
        assert len(result.errors) > 0

    def test_config_validation_malformed_config(self):
        """Test validation with malformed configuration."""
        config = "not a dict"

        result = validate_config(config)
        assert not result.is_valid
        assert len(result.errors) > 0