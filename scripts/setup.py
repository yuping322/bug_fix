"""Setup script for the Multi-Agent Orchestration Platform."""

from setuptools import setup, find_packages
import os
import sys

# Read the contents of README.md
this_directory = os.path.abspath(os.path.dirname(__file__))
parent_directory = os.path.dirname(this_directory)  # Go up one level to project root
readme_path = os.path.join(parent_directory, "README.md")

with open(readme_path, encoding="utf-8") as f:
    long_description = f.read()

# Read version from pyproject.toml or define it here
__version__ = "0.1.0"

# Core dependencies
INSTALL_REQUIRES = [
    "anthropic>=0.7.0",
    "GitPython>=3.1.0",
    "langgraph>=0.0.20",
    "langchain>=0.1.0",
    "fastapi>=0.104.0",
    "typer>=0.9.0",
    "docker>=6.1.0",
    "pyyaml>=6.0",
    "structlog>=23.2.0",
    "rich>=13.7.0",
    "pydantic>=2.5.0",
    "uvloop>=0.19.0",
    "mcp>=0.1.0",
    "aiohttp>=3.9.0",  # For external service calls
    "httpx>=0.25.0",    # For async HTTP requests
]

# Development dependencies
DEV_REQUIRES = [
    "black>=23.0.0",
    "flake8>=6.0.0",
    "mypy>=1.0.0",
    "pre-commit>=3.0.0",
    "sphinx>=5.0.0",
    "sphinx-rtd-theme>=1.2.0",
]

# Test dependencies
TEST_REQUIRES = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.10.0",
    "pytest-xdist>=3.0.0",  # For parallel test execution
]

# Optional dependencies
EXTRAS_REQUIRE = {
    "dev": DEV_REQUIRES,
    "test": TEST_REQUIRES,
    "all": DEV_REQUIRES + TEST_REQUIRES,
}

# Entry points for console scripts
ENTRY_POINTS = {
    "console_scripts": [
        "mao=src.cli.main:app",
        "multi-agent-orchestration=src.cli.main:app",
        "agent-orchestration=src.cli.main:app",
    ],
}

setup(
    name="multi-agent-orchestration",
    version=__version__,
    description="Multi-Agent Code Development Orchestration Platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Multi-Agent Orchestration Team",
    author_email="team@mao-platform.com",
    url="https://github.com/your-org/multi-agent-orchestration",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Distributed Computing",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
    ],
    keywords="ai agents orchestration workflow automation development",
    packages=find_packages(where=".", include=["src*"]),
    package_dir={"": "."},
    include_package_data=True,
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRE,
    entry_points=ENTRY_POINTS,
    python_requires=">=3.11",
    zip_safe=False,
    project_urls={
        "Documentation": "https://mao-platform.readthedocs.io/",
        "Source": "https://github.com/your-org/multi-agent-orchestration",
        "Tracker": "https://github.com/your-org/multi-agent-orchestration/issues",
    },
)