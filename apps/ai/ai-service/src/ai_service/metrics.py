import time
from fastapi import FastAPI, Request
from starlette.responses import Response
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.util.types import Attributes
from starlette.middleware.base import RequestResponseEndpoint


def configure_metrics(app: FastAPI, resource: Resource, endpoint: str) -> None:
    reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=endpoint, insecure=True),
        export_interval_millis=10_000,  # Export metrics every 10 seconds
    )

    provider = MeterProvider(resource=resource, metric_readers=[reader])

    metrics.set_meter_provider(provider)

    meter = metrics.get_meter("ai_service")

    request_counter = meter.create_counter(
        name="ai_service.http.requests",
        description="Total number of HTTP request processed.",
        unit="{request}",
    )

    error_counter = meter.create_counter(
        name="ai_service.http.errors",
        description="Total number of HTTP requests resulting in server errors.",
        unit="{request}",
    )

    request_duration = meter.create_histogram(
        name="ai_service.http.request.duration",
        description="HTTP requests processing duration.",
        unit="s",
    )
    app.state.meter_provider = provider

    @app.middleware("http")
    async def collect_http_metrics(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.perf_counter()
        staus_code = 500

        try:
            response = await call_next(request)
            staus_code = response.status_code
            return response
        except Exception as e:
            error_counter.add(1)
            raise e
        finally:
            duration = time.perf_counter() - start_time
            route = request.scope.get("route")
            route_path = getattr(route, "path", "unmatched")

            attributes: Attributes = {
                "http.request.method": request.method,
                "http.route": route_path,
                "http.response.status_code": staus_code,
            }

            request_counter.add(1, attributes)
            request_duration.record(duration, attributes)

            if staus_code >= 500:
                error_counter.add(1, attributes)
