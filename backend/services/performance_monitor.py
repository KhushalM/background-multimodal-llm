import time
import logging
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import deque
import statistics

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Single performance measurement"""

    service: str
    operation: str
    duration: float
    timestamp: float
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceStats:
    """Statistics for a service"""

    service_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_duration: float = 0.0
    min_duration: float = float("inf")
    max_duration: float = 0.0
    recent_durations: deque = field(default_factory=lambda: deque(maxlen=100))


class PerformanceMonitor:
    """Monitor and optimize pipeline performance"""

    def __init__(self, max_history: int = 1000):
        self.metrics: deque = deque(maxlen=max_history)
        self.service_stats: Dict[str, ServiceStats] = {}

        # Performance thresholds (in seconds)
        self.thresholds = {
            "stt": 60.0,  # STT should be under 3s
            "multimodal": 20.0,  # AI response (includes screen analysis) under 5s
            "tts": 40.0,  # TTS under 4s
            "total_pipeline": 60.0,  # Total under 10s
        }

        # Optimization flags
        self.optimizations = {
            "parallel_processing": True,
            "caching_enabled": True,
            "batch_processing": False,
            "early_termination": True,
        }

    def record_metric(
        self,
        service: str,
        operation: str,
        duration: float,
        success: bool = True,
        metadata: Dict[str, Any] = None,
    ):
        """Record a performance metric"""
        metric = PerformanceMetric(
            service=service,
            operation=operation,
            duration=duration,
            timestamp=time.time(),
            success=success,
            metadata=metadata or {},
        )

        self.metrics.append(metric)
        self._update_service_stats(metric)

        # Check for performance issues
        self._check_performance_alert(metric)

    def _update_service_stats(self, metric: PerformanceMetric):
        """Update statistics for a service"""
        service = metric.service

        if service not in self.service_stats:
            self.service_stats[service] = ServiceStats(service_name=service)

        stats = self.service_stats[service]
        stats.total_requests += 1

        if metric.success:
            stats.successful_requests += 1
            stats.recent_durations.append(metric.duration)

            # Update duration statistics
            stats.min_duration = min(stats.min_duration, metric.duration)
            stats.max_duration = max(stats.max_duration, metric.duration)

            if stats.recent_durations:
                stats.avg_duration = statistics.mean(stats.recent_durations)
        else:
            stats.failed_requests += 1

    def _check_performance_alert(self, metric: PerformanceMetric):
        """Check if metric exceeds performance thresholds"""
        threshold = self.thresholds.get(metric.service)

        if threshold and metric.duration > threshold:
            logger.warning(
                f"Performance alert: {metric.service} {metric.operation} "
                f"took {metric.duration:.2f}s (threshold: {threshold:.1f}s)"
            )

            # Suggest optimizations
            self._suggest_optimizations(metric)

    def _suggest_optimizations(self, metric: PerformanceMetric):
        """Suggest optimizations based on performance issues"""
        service = metric.service

        if service == "stt" and metric.duration > self.thresholds["stt"]:
            logger.info("STT optimization suggestions:")
            logger.info("- Use smaller audio chunks")
            logger.info("- Current model: distil-whisper/distil-large-v3.5 (already optimized)")
            logger.info("- Implement audio preprocessing")

        elif service == "multimodal" and metric.duration > self.thresholds["multimodal"]:
            logger.info("Multimodal optimization suggestions:")
            logger.info("- Reduce max_tokens in config")
            logger.info("- Current model: gemini-2.0-flash-exp (already fast)")
            logger.info("- Implement response caching")
            logger.info("- Reduce screen image resolution if using screen context")
            logger.info("- Increase screen analysis cache duration")

        elif service == "tts" and metric.duration > self.thresholds["tts"]:
            logger.info("TTS optimization suggestions:")
            logger.info("- Use shorter text inputs")
            logger.info("- Current model: microsoft/speecht5_tts (balanced performance)")
            logger.info("- Enable batch processing")

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for all services"""
        summary = {
            "total_metrics": len(self.metrics),
            "services": {},
            "overall_health": "good",
        }

        for service_name, stats in self.service_stats.items():
            success_rate = (stats.successful_requests / stats.total_requests * 100) if stats.total_requests > 0 else 0

            service_summary = {
                "total_requests": stats.total_requests,
                "success_rate": round(success_rate, 1),
                "avg_duration": round(stats.avg_duration, 2),
                "min_duration": round(stats.min_duration, 2),
                "max_duration": round(stats.max_duration, 2),
                "health_status": self._get_service_health(stats),
            }

            summary["services"][service_name] = service_summary

        # Determine overall health
        health_scores = [s.get("health_status", "good") for s in summary["services"].values()]
        if "poor" in health_scores:
            summary["overall_health"] = "poor"
        elif "fair" in health_scores:
            summary["overall_health"] = "fair"

        return summary

    def _get_service_health(self, stats: ServiceStats) -> str:
        """Determine health status for a service"""
        if stats.total_requests == 0:
            return "unknown"

        success_rate = stats.successful_requests / stats.total_requests
        avg_duration = stats.avg_duration
        threshold = self.thresholds.get(stats.service_name, 5.0)

        if success_rate < 0.8 or avg_duration > threshold * 1.5:
            return "poor"
        elif success_rate < 0.95 or avg_duration > threshold:
            return "fair"
        else:
            return "good"

    def get_optimization_recommendations(self) -> List[str]:
        """Get optimization recommendations based on current performance"""
        recommendations = []

        for service_name, stats in self.service_stats.items():
            if stats.total_requests < 5:  # Not enough data
                continue

            success_rate = stats.successful_requests / stats.total_requests
            threshold = self.thresholds.get(service_name, 5.0)

            if success_rate < 0.9:
                recommendations.append(f"Improve {service_name} reliability (success rate: {success_rate:.1%})")

            if stats.avg_duration > threshold:
                recommendations.append(f"Optimize {service_name} performance (avg: {stats.avg_duration:.1f}s)")

        # Pipeline-level recommendations
        total_avg = sum(stats.avg_duration for stats in self.service_stats.values())
        if total_avg > self.thresholds["total_pipeline"]:
            recommendations.append("Consider parallel processing to reduce total pipeline time")

        if not recommendations:
            recommendations.append("Performance is within acceptable limits")

        return recommendations

    def optimize_automatically(self) -> Dict[str, Any]:
        """Apply automatic optimizations based on performance data"""
        optimizations_applied = []

        # Check if we should enable parallel processing
        stt_stats = self.service_stats.get("stt")
        tts_stats = self.service_stats.get("tts")

        if stt_stats and tts_stats and stt_stats.avg_duration > 2.0 and tts_stats.avg_duration > 2.0:
            if not self.optimizations["parallel_processing"]:
                self.optimizations["parallel_processing"] = True
                optimizations_applied.append("Enabled parallel STT/TTS processing")

        # Check if we should enable caching
        multimodal_stats = self.service_stats.get("multimodal")
        if multimodal_stats and multimodal_stats.avg_duration > 3.0:
            if not self.optimizations["caching_enabled"]:
                self.optimizations["caching_enabled"] = True
                optimizations_applied.append("Enabled response caching")

        # Check for batch processing opportunities
        if tts_stats and tts_stats.total_requests > 10 and tts_stats.avg_duration > 3.0:
            if not self.optimizations["batch_processing"]:
                self.optimizations["batch_processing"] = True
                optimizations_applied.append("Enabled TTS batch processing")

        return {
            "optimizations_applied": optimizations_applied,
            "current_optimizations": self.optimizations.copy(),
        }

    def reset_metrics(self):
        """Reset all performance metrics"""
        self.metrics.clear()
        self.service_stats.clear()
        logger.info("Performance metrics reset")


# Context manager for easy metric recording
class PerformanceTimer:
    """Context manager for timing operations"""

    def __init__(
        self,
        monitor: PerformanceMonitor,
        service: str,
        operation: str,
        metadata: Dict[str, Any] = None,
    ):
        self.monitor = monitor
        self.service = service
        self.operation = operation
        self.metadata = metadata or {}
        self.start_time = None

    async def __aenter__(self):
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        success = exc_type is None

        self.monitor.record_metric(
            service=self.service,
            operation=self.operation,
            duration=duration,
            success=success,
            metadata=self.metadata,
        )

        return False  # Don't suppress exceptions


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


# Decorator for automatic performance monitoring
def monitor_performance(service: str, operation: str = None):
    """Decorator to automatically monitor function performance"""

    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            op_name = operation or func.__name__
            async with PerformanceTimer(performance_monitor, service, op_name):
                return await func(*args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            op_name = operation or func.__name__
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                performance_monitor.record_metric(service, op_name, duration, success)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
