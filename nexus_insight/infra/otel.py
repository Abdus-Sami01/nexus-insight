import functools
import logging
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from nexus_insight.config import settings

logger = logging.getLogger(__name__)

# Initialize tracing if endpoint is provided
if settings.OTEL_EXPORTER_ENDPOINT:
    try:
        resource = Resource(attributes={"service.name": "nexus-insight"})
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_ENDPOINT, insecure=True))
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
    except Exception as e:
        logger.warning(f"Failed to initialize OTEL tracing: {e}")

tracer = trace.get_tracer(__name__)

def trace_node(node_name: str):
    """Decorator to trace LangGraph nodes"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Check if first arg is 'self' (for methods) or 'state'
            if len(args) > 0 and hasattr(args[0], "__class__") and not isinstance(args[0], dict):
                # Probably a method, 'self' is args[0], 'state' is args[1]
                state = args[1] if len(args) > 1 else {}
            else:
                state = args[0] if len(args) > 0 else {}

            with tracer.start_as_current_span(f"node:{node_name}") as span:
                span.set_attribute("nexus.node", node_name)
                span.set_attribute("nexus.session_id", state.get("session_id", "unknown") if isinstance(state, dict) else "unknown")
                span.set_attribute("nexus.revision", state.get("revision_count", 0) if isinstance(state, dict) else 0)
                
                try:
                    result = await func(*args, **kwargs)
                    if isinstance(result, dict) and "confidence_score" in result:
                        span.set_attribute("nexus.confidence", result["confidence_score"])
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR))
                    raise
        return wrapper
    return decorator
