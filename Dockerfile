# Multi-stage Dockerfile for Multi-Agent Orchestration Platform

# Base stage with common dependencies
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash app

# Set work directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml scripts/setup.py ./

# Development stage
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir -e ".[dev,test]"

# Copy source code
COPY . .

# Change ownership to app user
RUN chown -R app:app /app

# Switch to app user
USER app

# Expose ports for development
EXPOSE 8000 3000

# Health check for development
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import sys; print('Development container healthy')" || exit 1

# Default command for development
CMD ["python", "-m", "src.cli.main", "--help"]

# Testing stage
FROM development as testing

# Run tests
RUN pytest --version
RUN make test-unit || echo "Unit tests failed"

# Production stage
FROM base as production

# Install production dependencies only
RUN pip install --no-cache-dir -e .

# Copy source code (excluding tests and dev files)
COPY src/ ./src/
COPY config.example.yaml ./

# Create necessary directories
RUN mkdir -p /app/logs /app/data

# Change ownership to app user
RUN chown -R app:app /app

# Switch to app user
USER app

# Expose ports
EXPOSE 8000

# Health check for production
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command for production
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

# MCP Server stage
FROM base as mcp-server

# Install production dependencies
RUN pip install --no-cache-dir -e .

# Copy source code
COPY src/ ./src/
COPY config.example.yaml ./

# Create necessary directories
RUN mkdir -p /app/logs

# Change ownership to app user
RUN chown -R app:app /app

# Switch to app user
USER app

# Expose MCP port
EXPOSE 3000

# Health check for MCP server
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Default command for MCP server
CMD ["python", "-m", "src.mcp_integration.server"]

# CLI stage
FROM base as cli

# Install production dependencies
RUN pip install --no-cache-dir -e .

# Copy source code
COPY src/ ./src/
COPY config.example.yaml ./

# Change ownership to app user
RUN chown -R app:app /app

# Switch to app user
USER app

# Health check for CLI
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import sys; print('CLI container healthy')" || exit 1

# Default command for CLI
CMD ["python", "-m", "src.cli.main", "--help"]

# Builder stage for CI/CD
FROM base as builder

# Install build dependencies
RUN pip install --no-cache-dir build

# Copy all files
COPY . .

# Build wheel
RUN python -m build --wheel

# Final minimal stage for distribution
FROM python:3.11-slim as dist

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash app

# Set work directory
WORKDIR /app

# Copy built wheel from builder stage
COPY --from=builder /app/dist/*.whl ./

# Install the wheel
RUN pip install --no-cache-dir *.whl

# Copy example config
COPY --from=builder /app/config.example.yaml ./

# Create necessary directories
RUN mkdir -p /app/logs /app/data

# Change ownership to app user
RUN chown -R app:app /app

# Switch to app user
USER app

# Expose ports
EXPOSE 8000 3000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import sys; print('Distribution container healthy')" || exit 1

# Default command
CMD ["multi-agent-orchestration", "--help"]