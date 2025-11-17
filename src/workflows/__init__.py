"""Multi-Agent Orchestration Platform - Workflows Module."""

from .templates import CodeReviewTemplate as CodeReview, PRAutomationTemplate as PRAutomation, TaskDevelopmentTemplate as TaskDevelopment

__all__ = [
    "CodeReview",
    "PRAutomation",
    "TaskDevelopment",
]