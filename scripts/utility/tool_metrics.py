"""
Tool metrics and monitoring system for tracking tool usage, performance, and reliability.

This module provides comprehensive metrics collection for AI tools including:
- Usage statistics
- Performance metrics 
- Error rates and retry patterns
- Cache hit rates for tool responses
"""

import time
import json
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, deque
import asyncio
from functools import wraps
from contextvars import ContextVar

# Setup logging
from ..logging_config import get_utility_logger
logger = get_utility_logger('ai_tools.tool_metrics')

# Langfuse integration
try:
    from langfuse import get_client
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False

# Global context variable for parent span tracking
_current_span: ContextVar[Optional[Any]] = ContextVar('current_span', default=None)


@dataclass
class ToolCallMetrics:
    """Metrics for a single tool call."""
    tool_name: str
    start_time: float
    end_time: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    retry_count: int = 0
    response_size: int = 0
    cached: bool = False
    execution_context: Dict[str, Any] = None
    
    @property
    def duration_ms(self) -> float:
        """Get execution duration in milliseconds."""
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


class ToolMetricsCollector:
    """
    Collects and manages tool usage metrics.
    
    Features:
    - Real-time metrics collection
    - Periodic aggregation and reporting
    - Performance monitoring
    - Error tracking and alerting
    """
    
    def __init__(self, metrics_file: Optional[Path] = None):
        """
        Initialize metrics collector.
        
        Args:
            metrics_file: Optional path to persist metrics
        """
        self.metrics_file = metrics_file or Path("tool_metrics.json")
        self.active_calls: Dict[str, ToolCallMetrics] = {}
        self.completed_calls: deque = deque(maxlen=1000)  # Keep last 1000 calls
        self.aggregated_metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'total_calls': 0,
            'success_count': 0,
            'error_count': 0,
            'total_duration_ms': 0.0,
            'avg_duration_ms': 0.0,
            'retry_count': 0,
            'cache_hits': 0,
            'last_error': None,
            'error_types': defaultdict(int)
        })
        
        self._load_persisted_metrics()
    
    def start_tool_call(self, tool_name: str, context: Dict[str, Any] = None) -> str:
        """
        Start tracking a tool call.
        
        Args:
            tool_name: Name of the tool being called
            context: Additional context information
            
        Returns:
            str: Unique call ID for tracking
        """
        call_id = f"{tool_name}_{time.time()}_{id(context) if context else 0}"
        
        metrics = ToolCallMetrics(
            tool_name=tool_name,
            start_time=time.time(),
            execution_context=context or {}
        )
        
        self.active_calls[call_id] = metrics
        logger.debug(f"Started tracking tool call: {call_id}")
        
        return call_id
    
    def end_tool_call(
        self, 
        call_id: str, 
        success: bool = True, 
        error_message: Optional[str] = None,
        retry_count: int = 0,
        response_size: int = 0,
        cached: bool = False
    ) -> Optional[ToolCallMetrics]:
        """
        End tracking a tool call.
        
        Args:
            call_id: Call ID from start_tool_call
            success: Whether the call succeeded
            error_message: Error message if failed
            retry_count: Number of retries performed
            response_size: Size of response in bytes
            cached: Whether response was cached
            
        Returns:
            Optional[ToolCallMetrics]: Completed metrics or None if call_id not found
        """
        if call_id not in self.active_calls:
            logger.warning(f"Tool call {call_id} not found in active calls")
            return None
        
        metrics = self.active_calls.pop(call_id)
        metrics.end_time = time.time()
        metrics.success = success
        metrics.error_message = error_message
        metrics.retry_count = retry_count
        metrics.response_size = response_size
        metrics.cached = cached
        
        # Add to completed calls
        self.completed_calls.append(metrics)
        
        # Update aggregated metrics
        self._update_aggregated_metrics(metrics)
        
        logger.debug(f"Completed tool call: {call_id} (success={success}, duration={metrics.duration_ms:.2f}ms)")
        
        return metrics
    
    def _update_aggregated_metrics(self, metrics: ToolCallMetrics) -> None:
        """Update aggregated metrics with completed call."""
        tool_metrics = self.aggregated_metrics[metrics.tool_name]
        
        tool_metrics['total_calls'] += 1
        tool_metrics['total_duration_ms'] += metrics.duration_ms
        tool_metrics['avg_duration_ms'] = tool_metrics['total_duration_ms'] / tool_metrics['total_calls']
        tool_metrics['retry_count'] += metrics.retry_count
        
        if metrics.success:
            tool_metrics['success_count'] += 1
        else:
            tool_metrics['error_count'] += 1
            tool_metrics['last_error'] = metrics.error_message
            if metrics.error_message:
                # Categorize error types
                error_type = self._categorize_error(metrics.error_message)
                tool_metrics['error_types'][error_type] += 1
        
        if metrics.cached:
            tool_metrics['cache_hits'] += 1
    
    def _categorize_error(self, error_message: str) -> str:
        """Categorize error message into error type."""
        error_lower = error_message.lower()
        
        if 'timeout' in error_lower or 'timed out' in error_lower:
            return 'timeout'
        elif 'connection' in error_lower or 'network' in error_lower:
            return 'network'
        elif 'rate limit' in error_lower or 'too many requests' in error_lower:
            return 'rate_limit'
        elif 'authentication' in error_lower or 'unauthorized' in error_lower:
            return 'auth'
        elif 'not found' in error_lower or '404' in error_lower:
            return 'not_found'
        elif 'server error' in error_lower or '500' in error_lower:
            return 'server_error'
        else:
            return 'other'
    
    def get_tool_metrics(self, tool_name: str) -> Dict[str, Any]:
        """
        Get aggregated metrics for a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Dict containing tool metrics
        """
        metrics = dict(self.aggregated_metrics[tool_name])
        
        # Add calculated fields
        total_calls = metrics['total_calls']
        if total_calls > 0:
            metrics['success_rate'] = (metrics['success_count'] / total_calls) * 100
            metrics['error_rate'] = (metrics['error_count'] / total_calls) * 100
            metrics['cache_hit_rate'] = (metrics['cache_hits'] / total_calls) * 100
        else:
            metrics['success_rate'] = 0.0
            metrics['error_rate'] = 0.0
            metrics['cache_hit_rate'] = 0.0
        
        return metrics
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get aggregated metrics for all tools.
        
        Returns:
            Dict mapping tool names to their metrics
        """
        return {tool_name: self.get_tool_metrics(tool_name) 
                for tool_name in self.aggregated_metrics.keys()}
    
    def get_recent_calls(self, tool_name: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent tool calls.
        
        Args:
            tool_name: Filter by tool name (None for all tools)
            limit: Maximum number of calls to return
            
        Returns:
            List of recent call metrics
        """
        calls = []
        for metrics in reversed(self.completed_calls):
            if tool_name and metrics.tool_name != tool_name:
                continue
            calls.append(metrics.to_dict())
            if len(calls) >= limit:
                break
        
        return calls
    
    def reset_metrics(self, tool_name: Optional[str] = None) -> None:
        """
        Reset metrics for a tool or all tools.
        
        Args:
            tool_name: Tool to reset (None for all tools)
        """
        if tool_name:
            if tool_name in self.aggregated_metrics:
                del self.aggregated_metrics[tool_name]
                logger.info(f"Reset metrics for tool: {tool_name}")
        else:
            self.aggregated_metrics.clear()
            self.completed_calls.clear()
            self.active_calls.clear()
            logger.info("Reset all tool metrics")
    
    def _load_persisted_metrics(self) -> None:
        """Load persisted metrics from file."""
        if not self.metrics_file.exists():
            return
        
        try:
            with open(self.metrics_file, 'r') as f:
                data = json.load(f)
                
            # Load aggregated metrics
            for tool_name, metrics in data.get('aggregated_metrics', {}).items():
                self.aggregated_metrics[tool_name].update(metrics)
                
            logger.info(f"Loaded persisted metrics from {self.metrics_file}")
            
        except Exception as e:
            logger.warning(f"Failed to load persisted metrics: {e}")
    
    def persist_metrics(self) -> None:
        """Persist current metrics to file."""
        try:
            data = {
                'aggregated_metrics': dict(self.aggregated_metrics),
                'timestamp': datetime.now().isoformat(),
                'recent_calls': self.get_recent_calls(limit=50)  # Save last 50 calls
            }
            
            with open(self.metrics_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
            logger.debug(f"Persisted metrics to {self.metrics_file}")
            
        except Exception as e:
            logger.error(f"Failed to persist metrics: {e}")
    
    def generate_report(self) -> str:
        """
        Generate a human-readable metrics report.
        
        Returns:
            str: Formatted metrics report
        """
        report_lines = ["# Tool Metrics Report", ""]
        
        all_metrics = self.get_all_metrics()
        
        if not all_metrics:
            return "# Tool Metrics Report\n\nNo metrics available."
        
        # Summary section
        total_calls = sum(m['total_calls'] for m in all_metrics.values())
        total_errors = sum(m['error_count'] for m in all_metrics.values())
        
        report_lines.extend([
            "## Summary",
            f"- **Total Tool Calls**: {total_calls}",
            f"- **Total Errors**: {total_errors}",
            f"- **Overall Success Rate**: {((total_calls - total_errors) / total_calls * 100):.1f}%" if total_calls > 0 else "- **Overall Success Rate**: N/A",
            ""
        ])
        
        # Per-tool metrics
        report_lines.append("## Tool Metrics")
        
        for tool_name, metrics in sorted(all_metrics.items()):
            report_lines.extend([
                f"### {tool_name}",
                f"- **Total Calls**: {metrics['total_calls']}",
                f"- **Success Rate**: {metrics['success_rate']:.1f}%",
                f"- **Average Duration**: {metrics['avg_duration_ms']:.2f}ms",
                f"- **Cache Hit Rate**: {metrics['cache_hit_rate']:.1f}%",
                f"- **Total Retries**: {metrics['retry_count']}",
                ""
            ])
            
            if metrics['error_count'] > 0:
                report_lines.append("  **Error Types:**")
                for error_type, count in metrics['error_types'].items():
                    report_lines.append(f"  - {error_type}: {count}")
                report_lines.append("")
        
        return "\n".join(report_lines)


# Global metrics collector instance
_global_metrics_collector: Optional[ToolMetricsCollector] = None


def get_metrics_collector() -> ToolMetricsCollector:
    """Get the global metrics collector instance."""
    global _global_metrics_collector
    if _global_metrics_collector is None:
        _global_metrics_collector = ToolMetricsCollector()
    return _global_metrics_collector


def track_tool_call(tool_name: str, context: Dict[str, Any] = None, is_root: bool = True):
    """
    Decorator for tracking tool call metrics and sending to Langfuse.

    Args:
        tool_name: Name of the tool
        context: Additional context information
        is_root: If True, creates a root span. If False, creates a child span under the current parent. Defaults to True.

    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            call_id = collector.start_tool_call(tool_name, context)

            # Initialize Langfuse span
            langfuse_span = None
            langfuse_client = None
            span_token = None

            if LANGFUSE_AVAILABLE:
                try:
                    langfuse_client = get_client()

                    # Get parent span from context (if not root)
                    parent_span = _current_span.get() if not is_root else None

                    logger.info(f"[LANGFUSE] Starting {'root' if is_root or not parent_span else 'child'} span for tool: {tool_name}")

                    # Extract function arguments for logging
                    func_args = {}
                    if args:
                        func_args['args'] = str(args)[:500]  # Limit size
                    if kwargs:
                        # Filter out Context object and other non-serializable items
                        filtered_kwargs = {k: str(v)[:500] for k, v in kwargs.items() if k != 'ctx'}
                        func_args['kwargs'] = filtered_kwargs

                    # Create span - either as root or child
                    if parent_span:
                        # Create child span under parent
                        langfuse_span = parent_span.start_span(
                            name=f"mcp-tool-{tool_name}",
                            input={
                                "tool_name": tool_name,
                                "function": func.__name__,
                                "arguments": func_args,
                                "context": context or {}
                            },
                            metadata={
                                "tool_type": "mcp",
                                "tool_name": tool_name,
                                "function_name": func.__name__,
                                "call_id": call_id,
                                "timestamp": time.time(),
                                "is_child_span": True
                            }
                        )
                        logger.info(f"[LANGFUSE] Child span created under parent for {tool_name}")
                    else:
                        # Create root span
                        langfuse_span = langfuse_client.start_span(
                            name=f"mcp-tool-{tool_name}",
                            input={
                                "tool_name": tool_name,
                                "function": func.__name__,
                                "arguments": func_args,
                                "context": context or {}
                            },
                            metadata={
                                "tool_type": "mcp",
                                "tool_name": tool_name,
                                "function_name": func.__name__,
                                "call_id": call_id,
                                "timestamp": time.time(),
                                "is_root_span": True
                            }
                        )
                        logger.info(f"[LANGFUSE] Root span created with ID: {langfuse_span.id}")

                    # Set this span as current span for downstream calls
                    span_token = _current_span.set(langfuse_span)

                except Exception as e:
                    logger.error(f"[LANGFUSE] Failed to start span for {tool_name}: {e}", exc_info=True)
            else:
                logger.warning(f"[LANGFUSE] Langfuse not available - tool call {tool_name} will not be tracked")

            start_time = time.time()

            try:
                logger.info(f"[TOOL_CALL] Executing {tool_name} with args: {kwargs.get('query', kwargs.get('icon_name', 'N/A'))}")
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                logger.info(f"[TOOL_CALL] {tool_name} completed successfully in {duration_ms:.2f}ms")

                # End local metrics collection
                collector.end_tool_call(
                    call_id,
                    success=True,
                    response_size=len(str(result)) if result else 0
                )

                # Update Langfuse span with success
                if langfuse_span:
                    try:
                        result_preview = str(result)[:1000] if result else ""
                        langfuse_span.update(
                            output={
                                "result_preview": result_preview,
                                "result_length": len(str(result)) if result else 0,
                                "success": True
                            },
                            metadata={
                                "duration_ms": duration_ms,
                                "success": True,
                                "result_size": len(str(result)) if result else 0
                            }
                        )
                        langfuse_span.end()
                        logger.info(f"[LANGFUSE] Span ended successfully for {tool_name}")

                        # Only flush for root spans
                        if is_root or not _current_span.get():
                            langfuse_client.flush()
                            logger.info(f"[LANGFUSE] Flushed data to Langfuse for root span {tool_name}")

                    except Exception as e:
                        logger.error(f"[LANGFUSE] Failed to update/end span for {tool_name}: {e}", exc_info=True)

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(f"[TOOL_CALL] {tool_name} failed after {duration_ms:.2f}ms: {e}", exc_info=True)

                # End local metrics collection with error
                collector.end_tool_call(
                    call_id,
                    success=False,
                    error_message=str(e)
                )

                # Update Langfuse span with error
                if langfuse_span:
                    try:
                        langfuse_span.update(
                            output={
                                "error": str(e),
                                "error_type": type(e).__name__,
                                "success": False
                            },
                            metadata={
                                "duration_ms": duration_ms,
                                "success": False,
                                "error_message": str(e),
                                "error_type": type(e).__name__
                            }
                        )
                        langfuse_span.end()
                        logger.info(f"[LANGFUSE] Span ended with error for {tool_name}")

                        # Only flush for root spans
                        if is_root or not _current_span.get():
                            langfuse_client.flush()
                            logger.info(f"[LANGFUSE] Flushed error data to Langfuse for root span {tool_name}")

                    except Exception as langfuse_error:
                        logger.error(f"[LANGFUSE] Failed to update/end span with error for {tool_name}: {langfuse_error}", exc_info=True)

                raise
            finally:
                # Reset context to parent span
                if span_token is not None:
                    _current_span.reset(span_token)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            call_id = collector.start_tool_call(tool_name, context)

            # Initialize Langfuse span
            langfuse_span = None
            langfuse_client = None
            span_token = None

            if LANGFUSE_AVAILABLE:
                try:
                    langfuse_client = get_client()

                    # Get parent span from context (if not root)
                    parent_span = _current_span.get() if not is_root else None

                    logger.info(f"[LANGFUSE] Starting {'root' if is_root or not parent_span else 'child'} span for tool: {tool_name}")

                    # Extract function arguments for logging
                    func_args = {}
                    if args:
                        func_args['args'] = str(args)[:500]
                    if kwargs:
                        filtered_kwargs = {k: str(v)[:500] for k, v in kwargs.items() if k != 'ctx'}
                        func_args['kwargs'] = filtered_kwargs

                    # Create span - either as root or child
                    if parent_span:
                        # Create child span under parent
                        langfuse_span = parent_span.start_span(
                            name=f"mcp-tool-{tool_name}",
                            input={
                                "tool_name": tool_name,
                                "function": func.__name__,
                                "arguments": func_args,
                                "context": context or {}
                            },
                            metadata={
                                "tool_type": "mcp",
                                "tool_name": tool_name,
                                "function_name": func.__name__,
                                "call_id": call_id,
                                "timestamp": time.time(),
                                "is_child_span": True
                            }
                        )
                        logger.info(f"[LANGFUSE] Child span created under parent for {tool_name}")
                    else:
                        # Create root span
                        langfuse_span = langfuse_client.start_span(
                            name=f"mcp-tool-{tool_name}",
                            input={
                                "tool_name": tool_name,
                                "function": func.__name__,
                                "arguments": func_args,
                                "context": context or {}
                            },
                            metadata={
                                "tool_type": "mcp",
                                "tool_name": tool_name,
                                "function_name": func.__name__,
                                "call_id": call_id,
                                "timestamp": time.time(),
                                "is_root_span": True
                            }
                        )
                        logger.info(f"[LANGFUSE] Root span created with ID: {langfuse_span.id}")

                    # Set this span as current span for downstream calls
                    span_token = _current_span.set(langfuse_span)

                except Exception as e:
                    logger.error(f"[LANGFUSE] Failed to start span for {tool_name}: {e}", exc_info=True)
            else:
                logger.warning(f"[LANGFUSE] Langfuse not available - tool call {tool_name} will not be tracked")

            start_time = time.time()

            try:
                logger.info(f"[TOOL_CALL] Executing {tool_name}")
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                logger.info(f"[TOOL_CALL] {tool_name} completed successfully in {duration_ms:.2f}ms")

                # End local metrics collection
                collector.end_tool_call(
                    call_id,
                    success=True,
                    response_size=len(str(result)) if result else 0
                )

                # Update Langfuse span with success
                if langfuse_span:
                    try:
                        result_preview = str(result)[:1000] if result else ""
                        langfuse_span.update(
                            output={
                                "result_preview": result_preview,
                                "result_length": len(str(result)) if result else 0,
                                "success": True
                            },
                            metadata={
                                "duration_ms": duration_ms,
                                "success": True,
                                "result_size": len(str(result)) if result else 0
                            }
                        )
                        langfuse_span.end()
                        logger.info(f"[LANGFUSE] Span ended successfully for {tool_name}")

                        # Only flush for root spans
                        if is_root or not _current_span.get():
                            langfuse_client.flush()
                            logger.info(f"[LANGFUSE] Flushed data to Langfuse for root span {tool_name}")

                    except Exception as e:
                        logger.error(f"[LANGFUSE] Failed to update/end span for {tool_name}: {e}", exc_info=True)

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(f"[TOOL_CALL] {tool_name} failed after {duration_ms:.2f}ms: {e}", exc_info=True)

                # End local metrics collection with error
                collector.end_tool_call(
                    call_id,
                    success=False,
                    error_message=str(e)
                )

                # Update Langfuse span with error
                if langfuse_span:
                    try:
                        langfuse_span.update(
                            output={
                                "error": str(e),
                                "error_type": type(e).__name__,
                                "success": False
                            },
                            metadata={
                                "duration_ms": duration_ms,
                                "success": False,
                                "error_message": str(e),
                                "error_type": type(e).__name__
                            }
                        )
                        langfuse_span.end()
                        logger.info(f"[LANGFUSE] Span ended with error for {tool_name}")

                        # Only flush for root spans
                        if is_root or not _current_span.get():
                            langfuse_client.flush()
                            logger.info(f"[LANGFUSE] Flushed error data to Langfuse for root span {tool_name}")

                    except Exception as langfuse_error:
                        logger.error(f"[LANGFUSE] Failed to update/end span with error for {tool_name}: {langfuse_error}", exc_info=True)

                raise
            finally:
                # Reset context to parent span
                if span_token is not None:
                    _current_span.reset(span_token)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator