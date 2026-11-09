import uvicorn
from fastapi import FastAPI

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.routes.fastapi_routes import add_a2a_routes_to_fastapi
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

from LongRunningExecutor import LongRunningExecutor

if __name__ == "__main__":
    agent_skill = AgentSkill(
        id="long_running_skill",
        name="SES Skill",
        description="I demonstrate SES lifecycle events",
        tags=["SES", "Task"],
    )

    agent_capability = AgentCapabilities(streaming=True)

    agent_card = AgentCard(
        name="Simple Event Schema (SES) Demo Server",
        description="",
        version="1.0",
        supported_interfaces=[
            AgentInterface(
                url="http://localhost:9999",
                protocol_binding="JSONRPC",
                protocol_version="1.0",
            )
        ],
        skills=[agent_skill],
        capabilities=agent_capability,
        default_input_modes=["text"],
        default_output_modes=["text"],
    )

    request_handler = DefaultRequestHandler(
        agent_executor=LongRunningExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )

    app = FastAPI()
    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(agent_card),
        jsonrpc_routes=create_jsonrpc_routes(request_handler, rpc_url="/"),
    )

    uvicorn.run(app, host="0.0.0.0", port=9999)
