"""Validation utilities module.

This module provides validation utilities for configuration,
data models, and runtime validation of various components.
"""

import os
import re
import json
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Generic
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from ..core.logging import get_logger
from ..core.security import InputValidator as SecurityInputValidator

logger = get_logger(__name__)

T = TypeVar('T')


class ValidationError(Exception):
    """Validation error with details."""

    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        super().__init__(message)
        self.field = field
        self.value = value


class ValidationSeverity(Enum):
    """Validation severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    infos: List[str]

    def __init__(self):
        self.is_valid = True
        self.errors = []
        self.warnings = []
        self.infos = []

    def add_error(self, message: str):
        """Add an error message."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)

    def add_info(self, message: str):
        """Add an info message."""
        self.infos.append(message)

    def merge(self, other: 'ValidationResult'):
        """Merge another validation result."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.infos.extend(other.infos)
        if not other.is_valid:
            self.is_valid = False


class Validator(Generic[T]):
    """Base validator class."""

    def validate(self, value: T) -> ValidationResult:
        """Validate a value.

        Args:
            value: Value to validate

        Returns:
            Validation result
        """
        raise NotImplementedError


class InputValidator(Validator[str]):
    """String validation with security enhancements."""

    def __init__(
        self,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
        required: bool = True,
        allowed_values: Optional[List[str]] = None
    ):
        """Initialize string validator with security checks."""
        self.min_length = min_length
        self.max_length = max_length or 1000  # Security: limit max length
        self.pattern = pattern
        self.required = required
        self.allowed_values = allowed_values

    def validate(self, value: str) -> ValidationResult:
        """Validate string with security checks."""
        result = ValidationResult()

        # Use security validator for sanitization
        try:
            sanitized = SecurityInputValidator.sanitize_string(value, self.max_length)
        except ValueError as e:
            result.add_error(str(e))
            return result

        # Check required
        if self.required and not sanitized:
            result.add_error("Value is required")
            return result

        # Check minimum length
        if self.min_length and len(sanitized) < self.min_length:
            result.add_error(f"Value must be at least {self.min_length} characters long")

        # Check pattern
        if self.pattern and not re.match(self.pattern, sanitized):
            result.add_error(f"Value does not match required pattern: {self.pattern}")

        # Check allowed values
        if self.allowed_values and sanitized not in self.allowed_values:
            result.add_error(f"Value must be one of: {', '.join(self.allowed_values)}")

        # Additional security checks
        if self._contains_suspicious_content(sanitized):
            result.add_error("Value contains suspicious content")

        return result

    def _contains_suspicious_content(self, value: str) -> bool:
        """Check for potentially malicious content."""
        # Check for script tags
        if re.search(r'<script[^>]*>.*?</script>', value, re.IGNORECASE):
            return True

        # Check for SQL injection patterns
        sql_patterns = [
            r';\s*(drop|delete|update|insert|alter)\s',
            r'union\s+select',
            r'--\s*$',
            r'/\*.*\*/'
        ]
        for pattern in sql_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True

        # Check for path traversal
        if '../' in value or '..\\' in value:
            return True

class NumberValidator(Validator[Union[int, float]]):
    """Number validation."""

    def __init__(
        self,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        required: bool = True,
        value_type: type = Union[int, float]
    ):
        """Initialize number validator.

        Args:
            min_value: Minimum value
            max_value: Maximum value
            required: Whether the number is required
            value_type: Expected number type (int or float)
        """
        self.min_value = min_value
        self.max_value = max_value
        self.required = required
        self.value_type = value_type

    def validate(self, value: Union[int, float]) -> ValidationResult:
        """Validate a number value."""
        result = ValidationResult()

        if self.required and value is None:
            result.add_error("Value is required")
            return result

        if value is None:
            return result

        if not isinstance(value, (int, float)):
            result.add_error(f"Expected number, got {type(value).__name__}")
            return result

        if self.value_type == int and not isinstance(value, int):
            result.add_error("Expected integer value")

        if self.min_value is not None and value < self.min_value:
            result.add_error(f"Value too small: minimum {self.min_value}")

        if self.max_value is not None and value > self.max_value:
            result.add_error(f"Value too large: maximum {self.max_value}")

        return result


class ListValidator(Validator[List[T]]):
    """List validation."""

    def __init__(
        self,
        item_validator: Optional[Validator[T]] = None,
        min_items: Optional[int] = None,
        max_items: Optional[int] = None,
        required: bool = True,
        unique: bool = False
    ):
        """Initialize list validator.

        Args:
            item_validator: Validator for list items
            min_items: Minimum number of items
            max_items: Maximum number of items
            required: Whether the list is required
            unique: Whether items must be unique
        """
        self.item_validator = item_validator
        self.min_items = min_items
        self.max_items = max_items
        self.required = required
        self.unique = unique

    def validate(self, value: List[T]) -> ValidationResult:
        """Validate a list value."""
        result = ValidationResult()

        if self.required and (value is None or len(value) == 0):
            result.add_error("List is required")
            return result

        if value is None:
            return result

        if not isinstance(value, list):
            result.add_error(f"Expected list, got {type(value).__name__}")
            return result

        if self.min_items is not None and len(value) < self.min_items:
            result.add_error(f"List too short: minimum {self.min_items} items")

        if self.max_items is not None and len(value) > self.max_items:
            result.add_error(f"List too long: maximum {self.max_items} items")

        if self.unique and len(value) != len(set(value)):
            result.add_error("List items must be unique")

        if self.item_validator:
            for i, item in enumerate(value):
                item_result = self.item_validator.validate(item)
                if not item_result.is_valid:
                    for error in item_result.errors:
                        result.add_error(f"Item {i}: {error}")

        return result


class DictValidator(Validator[Dict[str, Any]]):
    """Dictionary validation."""

    def __init__(
        self,
        schema: Optional[Dict[str, Validator[Any]]] = None,
        required_keys: Optional[List[str]] = None,
        optional_keys: Optional[List[str]] = None,
        required: bool = True
    ):
        """Initialize dictionary validator.

        Args:
            schema: Validation schema for dictionary keys
            required_keys: Required keys
            optional_keys: Optional keys
            required: Whether the dictionary is required
        """
        self.schema = schema or {}
        self.required_keys = required_keys or []
        self.optional_keys = optional_keys or []
        self.required = required

    def validate(self, value: Dict[str, Any]) -> ValidationResult:
        """Validate a dictionary value."""
        result = ValidationResult()

        if self.required and value is None:
            result.add_error("Dictionary is required")
            return result

        if value is None:
            return result

        if not isinstance(value, dict):
            result.add_error(f"Expected dictionary, got {type(value).__name__}")
            return result

        # Check required keys
        for key in self.required_keys:
            if key not in value:
                result.add_error(f"Required key missing: {key}")

        # Check allowed keys
        allowed_keys = set(self.required_keys + self.optional_keys + list(self.schema.keys()))
        if allowed_keys:
            for key in value.keys():
                if key not in allowed_keys:
                    result.add_warning(f"Unexpected key: {key}")

        # Validate schema
        for key, validator in self.schema.items():
            if key in value:
                field_result = validator.validate(value[key])
                if not field_result.is_valid:
                    for error in field_result.errors:
                        result.add_error(f"Key '{key}': {error}")

        return result


def validate_config_file(config_path: Union[str, Path]) -> ValidationResult:
    """Validate a configuration file.

    Args:
        config_path: Path to configuration file

    Returns:
        Validation result
    """
    result = ValidationResult()

    try:
        path = Path(config_path)
        if not path.exists():
            result.add_error("Configuration file does not exist")
            return result

        if not path.is_file():
            result.add_error("Configuration path is not a file")
            return result

        if path.suffix.lower() not in ['.yaml', '.yml', '.json']:
            result.add_error("Unsupported configuration file format")
            return result

        # Try to parse the file
        if path.suffix.lower() in ['.yaml', '.yml']:
            import yaml
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        else:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

        if not isinstance(data, dict):
            result.add_error("Configuration must be a dictionary")
            return result

        # Basic structure validation
        if 'platform' not in data:
            result.add_error("Required configuration key missing: platform")

        if 'agents' not in data:
            result.add_error("Required configuration key missing: agents")

        if 'workflows' not in data:
            result.add_error("Required configuration key missing: workflows")

    except Exception as e:
        result.add_error(f"Failed to parse configuration file: {e}")

    return result


def validate_agent_config(agent_config: Dict[str, Any]) -> ValidationResult:
    """Validate agent configuration.

    Args:
        agent_config: Agent configuration dictionary

    Returns:
        Validation result
    """
    result = ValidationResult()

    schema = {
        'name': InputValidator(required=True, min_length=1, max_length=100),
        'type': InputValidator(required=True, allowed_values=['claude', 'codex', 'copilot']),
        'api_key': InputValidator(required=True, min_length=10),
        'model': InputValidator(required=False, min_length=1),
        'max_tokens': NumberValidator(min_value=1, max_value=100000),
        'temperature': NumberValidator(min_value=0.0, max_value=2.0),
        'timeout': NumberValidator(min_value=1, max_value=300),
    }

    dict_validator = DictValidator(schema=schema, required=True)
    return dict_validator.validate(agent_config)


def validate_workflow_config(workflow_config: Dict[str, Any]) -> ValidationResult:
    """Validate workflow configuration.

    Args:
        workflow_config: Workflow configuration dictionary

    Returns:
        Validation result
    """
    result = ValidationResult()

    schema = {
        'name': InputValidator(required=True, min_length=1, max_length=100),
        'type': InputValidator(required=True, allowed_values=['simple', 'langgraph']),
        'description': InputValidator(required=False, max_length=500),
        'agents': ListValidator(item_validator=InputValidator(min_length=1), required=True, min_items=1),
        'steps': ListValidator(required=True, min_items=1),
        'config': DictValidator(required=False),
        'enabled': InputValidator(required=False, allowed_values=['true', 'false', 'True', 'False']),
        'metadata': DictValidator(required=False),
    }

    dict_validator = DictValidator(schema=schema, required=True)
    return dict_validator.validate(workflow_config)


def validate_config(config: Dict[str, Any]) -> List[str]:
    """Validate platform configuration.

    Args:
        config: Configuration dictionary to validate

    Returns:
        List of validation error messages
    """
    errors = []

    if not isinstance(config, dict):
        errors.append("Configuration must be a dictionary")
        return errors

    # Check required top-level keys
    required_keys = ['version', 'agents', 'workflows']
    for key in required_keys:
        if key not in config:
            errors.append(f"Required configuration key missing: {key}")

    # Validate version
    if 'version' in config:
        version = config['version']
        if not isinstance(version, str):
            errors.append("Version must be a string")
        elif not re.match(r'^\d+\.\d+\.\d+$', version):
            errors.append("Version must follow semantic versioning (x.y.z)")

    # Validate agents
    if 'agents' in config:
        if not isinstance(config['agents'], dict):
            errors.append("Agents must be a dictionary")
        else:
            for agent_name, agent_config in config['agents'].items():
                if not isinstance(agent_config, dict):
                    errors.append(f"Agent '{agent_name}' configuration must be a dictionary")
                    continue

                # Check required agent fields
                required_agent_fields = ['provider', 'model']
                for field in required_agent_fields:
                    if field not in agent_config:
                        errors.append(f"Agent '{agent_name}' missing required field: {field}")

                # Validate provider
                if 'provider' in agent_config:
                    provider = agent_config['provider']
                    valid_providers = ['anthropic', 'openai', 'github']
                    if provider not in valid_providers:
                        errors.append(f"Agent '{agent_name}' has invalid provider '{provider}'. Must be one of: {', '.join(valid_providers)}")

    # Validate workflows
    if 'workflows' in config:
        if not isinstance(config['workflows'], dict):
            errors.append("Workflows must be a dictionary")
        else:
            for workflow_name, workflow_config in config['workflows'].items():
                if not isinstance(workflow_config, dict):
                    errors.append(f"Workflow '{workflow_name}' configuration must be a dictionary")
                    continue

                # Check required workflow fields
                required_workflow_fields = ['type', 'steps']
                for field in required_workflow_fields:
                    if field not in workflow_config:
                        errors.append(f"Workflow '{workflow_name}' missing required field: {field}")

                # Validate workflow type
                if 'type' in workflow_config:
                    workflow_type = workflow_config['type']
                    valid_types = ['simple', 'langgraph']
                    if workflow_type not in valid_types:
                        errors.append(f"Workflow '{workflow_name}' has invalid type '{workflow_type}'. Must be one of: {', '.join(valid_types)}")

                # Validate steps
                if 'steps' in workflow_config:
                    steps = workflow_config['steps']
                    if not isinstance(steps, list):
                        errors.append(f"Workflow '{workflow_name}' steps must be a list")
                    elif len(steps) == 0:
                        errors.append(f"Workflow '{workflow_name}' must have at least one step")
                    else:
                        for i, step in enumerate(steps):
                            if not isinstance(step, dict):
                                errors.append(f"Workflow '{workflow_name}' step {i} must be a dictionary")
                                continue

                            # Check required step fields
                            if 'agent' not in step and 'agent_id' not in step:
                                errors.append(f"Workflow '{workflow_name}' step {i} missing agent field")

    return errors


def validate_config_file(config_file: Union[str, Path]) -> ValidationResult:
    """Validate a configuration file.

    Args:
        config_file: Path to the configuration file

    Returns:
        ValidationResult with validation status and messages
    """
    result = ValidationResult()

    try:
        config_path = Path(config_file)
        if not config_path.exists():
            result.errors.append(f"Configuration file not found: {config_file}")
            result.is_valid = False
            return result

        # Load configuration
        if config_path.suffix.lower() in ['.yaml', '.yml']:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        elif config_path.suffix.lower() == '.json':
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            result.errors.append(f"Unsupported configuration file format: {config_path.suffix}")
            result.is_valid = False
            return result

        # Validate configuration structure
        errors = validate_config(config)
        result.errors.extend(errors)

        # Check for additional validation rules
        if not config:
            result.errors.append("Configuration file is empty")
        elif not isinstance(config, dict):
            result.errors.append("Configuration must be a dictionary")

        # Validate version
        if 'version' not in config:
            result.errors.append("Required configuration key missing: version")

        # Validate platform (if present)
        if 'platform' in config:
            platform = config['platform']
            if not isinstance(platform, dict):
                result.errors.append("Platform configuration must be a dictionary")
            else:
                required_platform_fields = ['name', 'version']
                for field in required_platform_fields:
                    if field not in platform:
                        result.errors.append(f"Platform configuration missing required field: {field}")

        # Set validity
        result.is_valid = len(result.errors) == 0

    except Exception as e:
        result.errors.append(f"Failed to validate configuration: {str(e)}")
        result.is_valid = False

    return result