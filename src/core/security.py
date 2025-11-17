"""Security utilities for the multi-agent orchestration platform.

This module provides security hardening features including:
- Input validation and sanitization
- Credential encryption and secure storage
- Security headers and middleware
- Secure defaults and configuration
"""

import os
import re
import hashlib
import secrets
import base64
from typing import Any, Dict, Optional, Union, List
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import json

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..core.logging import get_logger

logger = get_logger(__name__)


class CredentialStoreType(str, Enum):
    """Types of credential storage."""

    LOCAL = "local"
    VAULT = "vault"
    AWS_SECRETS = "aws_secrets"
    AZURE_KEYVAULT = "azure_keyvault"
    GCP_SECRETS = "gcp_secrets"


class EncryptionError(Exception):
    """Encryption/decryption error."""

    pass


class CredentialManager:
    """Manages secure storage and retrieval of credentials."""

    def __init__(self, store_type: CredentialStoreType = CredentialStoreType.LOCAL,
                 encryption_key: Optional[str] = None):
        """Initialize credential manager.

        Args:
            store_type: Type of credential store to use
            encryption_key: Encryption key for local storage
        """
        self.store_type = store_type
        self.encryption_key = encryption_key or self._generate_key()
        self._fernet = Fernet(self.encryption_key)

    def _generate_key(self) -> bytes:
        """Generate a new encryption key."""
        # Use a deterministic key based on environment for development
        # In production, this should be randomly generated and stored securely
        env_key = os.getenv("AGENT_ORCHESTRATION_ENCRYPTION_KEY")
        if env_key:
            # Derive key from environment variable
            salt = b"agent_orchestration_salt"
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            return base64.urlsafe_b64encode(kdf.derive(env_key.encode()))

        # Fallback: generate random key (not persistent!)
        logger.warning("No encryption key provided, using ephemeral key")
        return Fernet.generate_key()

    def encrypt_credential(self, credential: str) -> str:
        """Encrypt a credential.

        Args:
            credential: Plain text credential

        Returns:
            Encrypted credential as base64 string
        """
        try:
            encrypted = self._fernet.encrypt(credential.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error("Failed to encrypt credential", error=str(e))
            raise EncryptionError(f"Failed to encrypt credential: {e}")

    def decrypt_credential(self, encrypted_credential: str) -> str:
        """Decrypt a credential.

        Args:
            encrypted_credential: Encrypted credential as base64 string

        Returns:
            Plain text credential
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_credential.encode())
            decrypted = self._fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error("Failed to decrypt credential", error=str(e))
            raise EncryptionError(f"Failed to decrypt credential: {e}")

    def store_credential(self, key: str, credential: str) -> None:
        """Store an encrypted credential.

        Args:
            key: Credential key
            credential: Plain text credential
        """
        encrypted = self.encrypt_credential(credential)

        if self.store_type == CredentialStoreType.LOCAL:
            self._store_local(key, encrypted)
        else:
            # TODO: Implement other storage backends
            raise NotImplementedError(f"Credential store {self.store_type} not implemented")

    def retrieve_credential(self, key: str) -> Optional[str]:
        """Retrieve and decrypt a credential.

        Args:
            key: Credential key

        Returns:
            Plain text credential or None if not found
        """
        if self.store_type == CredentialStoreType.LOCAL:
            encrypted = self._retrieve_local(key)
            if encrypted:
                return self.decrypt_credential(encrypted)
        else:
            # TODO: Implement other storage backends
            raise NotImplementedError(f"Credential store {self.store_type} not implemented")

        return None

    def _get_credential_path(self, key: str) -> Path:
        """Get the file path for a credential."""
        # Use a secure directory for credentials
        cred_dir = Path.home() / ".agent-orchestration" / "credentials"
        cred_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        return cred_dir / f"{key}.enc"

    def _store_local(self, key: str, encrypted_credential: str) -> None:
        """Store credential locally."""
        cred_file = self._get_credential_path(key)
        with open(cred_file, 'w', encoding='utf-8') as f:
            json.dump({"encrypted": encrypted_credential}, f)
        cred_file.chmod(0o600)  # Restrict permissions

    def _retrieve_local(self, key: str) -> Optional[str]:
        """Retrieve credential from local storage."""
        cred_file = self._get_credential_path(key)
        if not cred_file.exists():
            return None

        try:
            with open(cred_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("encrypted")
        except Exception as e:
            logger.error("Failed to read credential file", key=key, error=str(e))
            return None


class InputValidator:
    """Input validation and sanitization utilities."""

    # Common validation patterns
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    URL_PATTERN = re.compile(r'^https?://[^\s/$.?#].[^\s]*$', re.IGNORECASE)
    API_KEY_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{20,}$')
    IDENTIFIER_PATTERN = re.compile(r'^[a-z][a-z0-9_-]*$')

    @staticmethod
    def sanitize_string(input_str: str, max_length: int = 1000) -> str:
        """Sanitize a string input.

        Args:
            input_str: Input string
            max_length: Maximum allowed length

        Returns:
            Sanitized string
        """
        if not isinstance(input_str, str):
            raise ValueError("Input must be a string")

        # Remove null bytes and control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', input_str)

        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
            logger.warning("Input truncated to maximum length", max_length=max_length)

        return sanitized.strip()

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email address format.

        Args:
            email: Email address to validate

        Returns:
            True if valid email format
        """
        return bool(InputValidator.EMAIL_PATTERN.match(email))

    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format.

        Args:
            url: URL to validate

        Returns:
            True if valid URL format
        """
        return bool(InputValidator.URL_PATTERN.match(url))

    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """Validate API key format.

        Args:
            api_key: API key to validate

        Returns:
            True if valid API key format
        """
        return bool(InputValidator.API_KEY_PATTERN.match(api_key))

    @staticmethod
    def validate_identifier(identifier: str) -> bool:
        """Validate identifier format (lowercase, alphanumeric, dash, underscore).

        Args:
            identifier: Identifier to validate

        Returns:
            True if valid identifier format
        """
        return bool(InputValidator.IDENTIFIER_PATTERN.match(identifier))

    @staticmethod
    def validate_file_path(file_path: str, base_dir: Optional[Path] = None) -> bool:
        """Validate file path for security.

        Args:
            file_path: File path to validate
            base_dir: Base directory to restrict paths to

        Returns:
            True if path is safe
        """
        try:
            path = Path(file_path).resolve()

            # Check for directory traversal
            if ".." in path.parts:
                return False

            # Check against base directory if provided
            if base_dir:
                base_dir = base_dir.resolve()
                if not path.is_relative_to(base_dir):
                    return False

            return True
        except Exception:
            return False

    @staticmethod
    def validate_workflow_input(inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize workflow inputs.

        Args:
            inputs: Raw workflow inputs

        Returns:
            Validated and sanitized inputs

        Raises:
            ValueError: If validation fails
        """
        validated = {}

        for key, value in inputs.items():
            # Validate key
            if not InputValidator.validate_identifier(key):
                raise ValueError(f"Invalid input key: {key}")

            # Sanitize string values
            if isinstance(value, str):
                validated[key] = InputValidator.sanitize_string(value)
            elif isinstance(value, (int, float, bool)):
                validated[key] = value
            elif isinstance(value, list):
                # Validate list elements
                validated[key] = [
                    InputValidator.sanitize_string(str(item)) if isinstance(item, str) else item
                    for item in value
                ]
            elif isinstance(value, dict):
                # Recursively validate nested dicts
                validated[key] = InputValidator.validate_workflow_input(value)
            else:
                # Convert to string for other types
                validated[key] = str(value)

        return validated


class SecurityHeaders:
    """Security headers for HTTP responses."""

    @staticmethod
    def get_default_headers() -> Dict[str, str]:
        """Get default security headers.

        Returns:
            Dictionary of security headers
        """
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }

    @staticmethod
    def get_api_headers() -> Dict[str, str]:
        """Get security headers for API responses.

        Returns:
            Dictionary of API security headers
        """
        headers = SecurityHeaders.get_default_headers()
        headers.update({
            "X-API-Version": "1.0",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        })
        return headers


class SecurityConfig:
    """Security configuration utilities."""

    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate a secure random token.

        Args:
            length: Token length in bytes

        Returns:
            Secure random token as hex string
        """
        return secrets.token_hex(length)

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """Hash a password with salt.

        Args:
            password: Plain text password
            salt: Optional salt, generated if not provided

        Returns:
            Tuple of (hashed_password, salt)
        """
        if not salt:
            salt = SecurityConfig.generate_secure_token(16)

        # Use PBKDF2 for password hashing
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=100000,
        )
        hash_bytes = kdf.derive(password.encode())
        hashed = base64.b64encode(hash_bytes).decode()

        return hashed, salt

    @staticmethod
    def verify_password(password: str, hashed: str, salt: str) -> bool:
        """Verify a password against its hash.

        Args:
            password: Plain text password
            hashed: Hashed password
            salt: Salt used for hashing

        Returns:
            True if password matches
        """
        expected_hash, _ = SecurityConfig.hash_password(password, salt)
        return secrets.compare_digest(expected_hash, hashed)

    @staticmethod
    def validate_security_config(config: Dict[str, Any]) -> List[str]:
        """Validate security configuration.

        Args:
            config: Security configuration dictionary

        Returns:
            List of validation error messages
        """
        errors = []

        # Validate encryption key
        encryption_key = config.get("encryption_key")
        if encryption_key and len(encryption_key) < 32:
            errors.append("Encryption key must be at least 32 characters long")

        # Validate credential store
        credential_store = config.get("credential_store", "local")
        valid_stores = [store.value for store in CredentialStoreType]
        if credential_store not in valid_stores:
            errors.append(f"Invalid credential store: {credential_store}. Must be one of {valid_stores}")

        # Validate token expiry
        token_expiry = config.get("token_expiry", 3600)
        if not isinstance(token_expiry, int) or token_expiry < 60:
            errors.append("Token expiry must be an integer >= 60 seconds")

        return errors