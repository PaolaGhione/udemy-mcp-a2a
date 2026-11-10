import os

import uvicorn
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.routes.fastapi_routes import add_a2a_routes_to_fastapi
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

from executor import HelloWorldAgentExecutor
from RedisTaskStore import RedisTaskStore  # Just for demo

# --- Setup OpenTelemetry Tracing ---

# Define the service name for Jaeger
resource = Resource.create({"service.name": "a2a-helloworld-service"})

# 1. Setup the Span Exporter (OTLP/HTTP for Jaeger)
span_exporter = OTLPSpanExporter(
    endpoint="http://host.docker.internal:4318/v1/traces"  # change to correct url
)

# 2. Setup the Batch Processor (efficiently sends spans in background)
span_processor = BatchSpanProcessor(span_exporter)

# 3. Setup the Provider and bind it globally
provider = TracerProvider(resource=resource)
provider.add_span_processor(span_processor)
trace.set_tracer_provider(provider)

# 4. Get a tracer instance
tracer = trace.get_tracer(__name__)

# --- End Setup OpenTelemetry ---

if __name__ == "__main__":
    agent_skill = AgentSkill(
        id="say_hello_skill",
        name="Hello Skill",
        description="I can say hello",
        tags=["Hello", "World"],
    )

    agent_card = AgentCard(
        name="Basic Server Agent (HelloWorld)",
        description="A2A Agent with Distributed Tracing",
        version="1.0",
        supported_interfaces=[
            AgentInterface(
                url="http://localhost:9999",
                protocol_binding="JSONRPC",
                protocol_version="1.0",
            )
        ],
        default_input_modes=["text"],
        default_output_modes=["text"],
        skills=[agent_skill],
        capabilities=AgentCapabilities(streaming=False),
    )

    # Switching between stores for the lecture demo:
    # set REDIS_URL (e.g. redis://localhost:6379/0) to persist tasks in Redis,
    # otherwise the tasks stay in the memory of this process.
    redis_url = os.getenv("REDIS_URL")
    task_store = RedisTaskStore(redis_url) if redis_url else InMemoryTaskStore()

    request_handler = DefaultRequestHandler(
        agent_executor=HelloWorldAgentExecutor(),
        task_store=task_store,
        agent_card=agent_card,
    )

    app = FastAPI()
    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(agent_card),
        jsonrpc_routes=create_jsonrpc_routes(request_handler, rpc_url="/"),
    )

    # Middleware to capture a span for every incoming request
    @app.middleware("http")
    async def a2a_tracing_middleware(request, call_next):
        # Start the span
        with tracer.start_as_current_span(
            f"A2A {request.method} {request.url.path}",
            attributes={
                "http.method": request.method,
                "http.url": str(request.url),
            },
        ) as span:
            response = await call_next(request)
            # Tag the span with the result status
            span.set_attribute("http.status_code", response.status_code)
            return response

    uvicorn.run(app, host="0.0.0.0", port=9999)
