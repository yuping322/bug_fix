"""Observability system for the multi-agent orchestration platform.

This module provides comprehensive observability including structured logging,
metrics collection, and tracing capabilities.
"""

import time
import json
import logging
import threading
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import structlog

from .config import ObservabilityConfig


class LogLevel(str, Enum):
    """Enumeration of log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class MetricType(str, Enum):
    """Enumeration of metric types."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricValue:
    """A single metric measurement."""

    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class TraceSpan:
    """A trace span for distributed tracing."""

    span_id: str
    trace_id: str
    name: str
    parent_span_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def duration(self) -> Optional[float]:
        """Get span duration in seconds."""
        if self.end_time is None:
            return None
        return self.end_time - self.start_time

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add an event to the span."""
        event = {
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {},
        }
        self.events.append(event)

    def finish(self):
        """Mark the span as finished."""
        self.end_time = time.time()


class StructuredLogger:
    """Structured logging implementation using structlog."""

    def __init__(self, config: ObservabilityConfig):
        """Initialize the structured logger.

        Args:
            config: Observability configuration
        """
        self.config = config
        self._logger = None
        self._setup_logger()

    def _setup_logger(self):
        """Set up the structured logger."""
        # Configure structlog
        shared_processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
        ]

        if self.config.log_format == "json":
            shared_processors.append(structlog.processors.JSONRenderer())
        else:
            shared_processors.append(
                structlog.processors.KeyValueRenderer(
                    key_order=["timestamp", "level", "logger", "event"]
                )
            )

        structlog.configure(
            processors=shared_processors,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        # Create standard library logger
        self._logger = logging.getLogger("agent_orchestration")
        self._logger.setLevel(getattr(logging, self.config.log_level.upper(), logging.INFO))

        # Remove existing handlers
        for handler in self._logger.handlers[:]:
            self._logger.removeHandler(handler)

        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter("%(message)s"))
        self._logger.addHandler(console_handler)

        # Add file handler if configured
        if self.config.log_file:
            file_handler = logging.FileHandler(self.config.log_file)
            file_handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(file_handler)

    def debug(self, event: str, **kwargs):
        """Log a debug message."""
        self._logger.debug(event, **kwargs)

    def info(self, event: str, **kwargs):
        """Log an info message."""
        self._logger.info(event, **kwargs)

    def warning(self, event: str, **kwargs):
        """Log a warning message."""
        self._logger.warning(event, **kwargs)

    def error(self, event: str, **kwargs):
        """Log an error message."""
        self._logger.error(event, **kwargs)

    def critical(self, event: str, **kwargs):
        """Log a critical message."""
        self._logger.critical(event, **kwargs)

    def log(self, level: LogLevel, event: str, **kwargs):
        """Log a message at the specified level."""
        log_method = getattr(self, level.value.lower(), self.info)
        log_method(event, **kwargs)

    def bind(self, **context) -> 'BoundLogger':
        """Bind context to the logger."""
        return BoundLogger(self._logger.bind(**context))


class BoundLogger:
    """A logger with bound context."""

    def __init__(self, bound_logger):
        """Initialize with a bound structlog logger."""
        self._logger = bound_logger

    def debug(self, event: str, **kwargs):
        """Log a debug message."""
        self._logger.debug(event, **kwargs)

    def info(self, event: str, **kwargs):
        """Log an info message."""
        self._logger.info(event, **kwargs)

    def warning(self, event: str, **kwargs):
        """Log a warning message."""
        self._logger.warning(event, **kwargs)

    def error(self, event: str, **kwargs):
        """Log an error message."""
        self._logger.error(event, **kwargs)

    def critical(self, event: str, **kwargs):
        """Log a critical message."""
        self._logger.critical(event, **kwargs)


class MetricsCollector:
    """Metrics collection and reporting."""

    def __init__(self, config: ObservabilityConfig):
        """Initialize the metrics collector.

        Args:
            config: Observability configuration
        """
        self.config = config
        self._metrics: Dict[str, MetricValue] = {}
        self._counters: Dict[str, Dict[str, float]] = {}
        self._gauges: Dict[str, Dict[str, float]] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def increment_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric.

        Args:
            name: Metric name
            value: Value to increment by
            labels: Metric labels
        """
        labels = labels or {}
        label_key = json.dumps(labels, sort_keys=True)

        with self._lock:
            if name not in self._counters:
                self._counters[name] = {}
            if label_key not in self._counters[name]:
                self._counters[name][label_key] = 0.0

            self._counters[name][label_key] += value

            # Update metric value
            self._metrics[name] = MetricValue(
                name=name,
                value=self._counters[name][label_key],
                labels=labels,
                metric_type=MetricType.COUNTER
            )

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric value.

        Args:
            name: Metric name
            value: Gauge value
            labels: Metric labels
        """
        labels = labels or {}
        label_key = json.dumps(labels, sort_keys=True)

        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = {}
            self._gauges[name][label_key] = value

            # Update metric value
            self._metrics[name] = MetricValue(
                name=name,
                value=value,
                labels=labels,
                metric_type=MetricType.GAUGE
            )

    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Observe a value in a histogram.

        Args:
            name: Metric name
            value: Observed value
            labels: Metric labels
        """
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = []
            self._histograms[name].append(value)

            # Update metric value (using latest value for now)
            self._metrics[name] = MetricValue(
                name=name,
                value=value,
                labels=labels or {},
                metric_type=MetricType.HISTOGRAM
            )

    def get_metric(self, name: str) -> Optional[MetricValue]:
        """Get a metric value.

        Args:
            name: Metric name

        Returns:
            Metric value or None if not found
        """
        return self._metrics.get(name)

    def get_all_metrics(self) -> List[MetricValue]:
        """Get all metrics.

        Returns:
            List of all metric values
        """
        with self._lock:
            return list(self._metrics.values())

    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._metrics.clear()
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()


class TraceCollector:
    """Distributed tracing collector."""

    def __init__(self, config: ObservabilityConfig):
        """Initialize the trace collector.

        Args:
            config: Observability configuration
        """
        self.config = config
        self._spans: Dict[str, TraceSpan] = {}
        self._lock = threading.Lock()

    def start_span(
        self,
        name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> str:
        """Start a new trace span.

        Args:
            name: Span name
            trace_id: Trace ID (generated if not provided)
            parent_span_id: Parent span ID
            attributes: Span attributes

        Returns:
            Span ID
        """
        import uuid

        span_id = str(uuid.uuid4())
        if trace_id is None:
            trace_id = str(uuid.uuid4())

        span = TraceSpan(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=name,
            attributes=attributes or {},
        )

        with self._lock:
            self._spans[span_id] = span

        return span_id

    def finish_span(self, span_id: str):
        """Finish a trace span.

        Args:
            span_id: Span ID to finish
        """
        with self._lock:
            if span_id in self._spans:
                self._spans[span_id].finish()

    def add_span_event(self, span_id: str, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add an event to a span.

        Args:
            span_id: Span ID
            name: Event name
            attributes: Event attributes
        """
        with self._lock:
            if span_id in self._spans:
                self._spans[span_id].add_event(name, attributes)

    def get_span(self, span_id: str) -> Optional[TraceSpan]:
        """Get a trace span.

        Args:
            span_id: Span ID

        Returns:
            Trace span or None if not found
        """
        return self._spans.get(span_id)

    def get_all_spans(self) -> List[TraceSpan]:
        """Get all trace spans.

        Returns:
            List of all spans
        """
        with self._lock:
            return list(self._spans.values())

    def cleanup_finished_spans(self, max_age_seconds: int = 3600):
        """Clean up old finished spans.

        Args:
            max_age_seconds: Maximum age of spans to keep
        """
        current_time = time.time()
        to_remove = []

        with self._lock:
            for span_id, span in self._spans.items():
                if (span.end_time is not None and
                    current_time - span.end_time > max_age_seconds):
                    to_remove.append(span_id)

            for span_id in to_remove:
                del self._spans[span_id]


class ObservabilityManager:
    """Central observability manager."""

    def __init__(self, config: ObservabilityConfig):
        """Initialize the observability manager.

        Args:
            config: Observability configuration
        """
        self.config = config
        self.logger = StructuredLogger(config)
        self.metrics = MetricsCollector(config)
        self.tracer = TraceCollector(config)

    def create_logger(self, **context) -> BoundLogger:
        """Create a logger with bound context.

        Args:
            **context: Context to bind to the logger

        Returns:
            Bound logger
        """
        return self.logger.bind(**context)

    def record_workflow_execution(self, workflow_id: str, execution_time: float, success: bool):
        """Record workflow execution metrics.

        Args:
            workflow_id: Workflow identifier
            execution_time: Execution time in seconds
            success: Whether execution was successful
        """
        # Record execution count
        self.metrics.increment_counter(
            "workflow_executions_total",
            labels={"workflow_id": workflow_id, "status": "success" if success else "failure"}
        )

        # Record execution time
        self.metrics.observe_histogram(
            "workflow_execution_duration_seconds",
            execution_time,
            labels={"workflow_id": workflow_id}
        )

    def record_agent_call(self, agent_id: str, execution_time: float, tokens_used: int, success: bool):
        """Record agent call metrics.

        Args:
            agent_id: Agent identifier
            execution_time: Execution time in seconds
            tokens_used: Number of tokens used
            success: Whether call was successful
        """
        # Record call count
        self.metrics.increment_counter(
            "agent_calls_total",
            labels={"agent_id": agent_id, "status": "success" if success else "failure"}
        )

        # Record execution time
        self.metrics.observe_histogram(
            "agent_call_duration_seconds",
            execution_time,
            labels={"agent_id": agent_id}
        )

        # Record token usage
        self.metrics.observe_histogram(
            "agent_tokens_used",
            tokens_used,
            labels={"agent_id": agent_id}
        )

    def start_workflow_trace(self, workflow_id: str, execution_id: str) -> str:
        """Start tracing a workflow execution.

        Args:
            workflow_id: Workflow identifier
            execution_id: Execution identifier

        Returns:
            Span ID
        """
        if not self.config.tracing_enabled:
            return ""

        return self.tracer.start_span(
            name=f"workflow_{workflow_id}",
            attributes={
                "workflow.id": workflow_id,
                "execution.id": execution_id,
            }
        )

    def start_agent_trace(self, agent_id: str, span_id: str) -> str:
        """Start tracing an agent call.

        Args:
            agent_id: Agent identifier
            span_id: Parent span ID

        Returns:
            New span ID
        """
        if not self.config.tracing_enabled:
            return ""

        return self.tracer.start_span(
            name=f"agent_{agent_id}",
            parent_span_id=span_id,
            attributes={"agent.id": agent_id}
        )

    def finish_trace(self, span_id: str):
        """Finish a trace span.

        Args:
            span_id: Span ID to finish
        """
        if span_id:
            self.tracer.finish_span(span_id)

    def get_system_status(self) -> Dict[str, Any]:
        """Get system observability status.

        Returns:
            System status information
        """
        return {
            "metrics": {
                "total_metrics": len(self.metrics.get_all_metrics()),
                "active_spans": len([s for s in self.tracer.get_all_spans() if s.end_time is None]),
            },
            "logging": {
                "level": self.config.log_level,
                "format": self.config.log_format,
                "file": self.config.log_file,
            },
            "tracing": {
                "enabled": self.config.tracing_enabled,
                "total_spans": len(self.tracer.get_all_spans()),
            },
        }


# Global observability manager instance
observability_manager = ObservabilityManager(ObservabilityConfig())