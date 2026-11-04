import logging

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry._logs import set_logger_provider

from ai_service.config import get_settings
from ai_service.metrics import configure_metrics


def configure_observability(app: FastAPI) -> None:
    settings = get_settings()
    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "deployment.environment": settings.app_environment,
        }
    )

    # Configure distributed tracing
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=settings.otl_exporter_otlp_endpoint,
                insecure=True,
            )
        )
    )
    trace.set_tracer_provider(tracer_provider)

    # Configure log export
    logger_provider = LoggerProvider(resource=resource)

    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(
                endpoint=settings.otl_exporter_otlp_endpoint,
                insecure=True,
            )
        )
    )
    set_logger_provider(logger_provider)
    logging.getLogger().addHandler(
        LoggingHandler(
            level=logging.NOTSET,
            logger_provider=logger_provider,
        )
    )

    set_global_textmap(TraceContextTextMapPropagator())
    app.state.logger_provider = logger_provider
    app.state.tracer_provider = tracer_provider
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()

    configure_metrics(
        app=app,
        resource=resource,
        endpoint=settings.otl_exporter_otlp_endpoint,
    )
